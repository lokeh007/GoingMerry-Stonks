#!/bin/bash
set -e

# Monitor Cloud Run Batch Job Performance
#
# Usage:
#   ./scripts/monitor-batch-job.sh <execution-id>
#   ./scripts/monitor-batch-job.sh prod-regular-screeners-batch-3-tht7w
#
# Or auto-detect latest execution for a job:
#   ./scripts/monitor-batch-job.sh --job prod-regular-screeners-batch-3

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Parse arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <execution-id>"
    echo "   or: $0 --job <job-name>"
    echo ""
    echo "Examples:"
    echo "  $0 prod-regular-screeners-batch-3-tht7w"
    echo "  $0 --job prod-regular-screeners-batch-3"
    exit 1
fi

if [ "$1" = "--job" ]; then
    if [ -z "$2" ]; then
        echo "Error: Job name required with --job flag"
        exit 1
    fi

    JOB_NAME="$2"
    echo "Fetching latest execution for job: ${JOB_NAME}..."

    # Get latest execution
    EXECUTION_ID=$(gcloud run jobs executions list \
        --job="${JOB_NAME}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format="value(metadata.name)" \
        --limit=1)

    if [ -z "$EXECUTION_ID" ]; then
        echo "Error: No executions found for job ${JOB_NAME}"
        exit 1
    fi

    echo "Latest execution: ${EXECUTION_ID}"
    echo ""
else
    EXECUTION_ID="$1"
fi

# Extract job name from execution ID (format: job-name-xxxxx)
JOB_NAME=$(echo "${EXECUTION_ID}" | sed -E 's/-[a-z0-9]{5}$//')

# Create temporary directory for analysis
TEMP_DIR="/tmp/batch-audit-${EXECUTION_ID}"
mkdir -p "${TEMP_DIR}"

# Fetch execution metadata
echo -e "${BLUE}Fetching execution metadata...${NC}"
gcloud run jobs executions describe "${EXECUTION_ID}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format=json > "${TEMP_DIR}/execution.json"

# Fetch logs
echo -e "${BLUE}Fetching logs (this may take 10-15 seconds)...${NC}"
gcloud logging read \
    "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME} AND resource.labels.location=${REGION} AND labels.\"run.googleapis.com/execution_name\"=${EXECUTION_ID}" \
    --project="${PROJECT_ID}" \
    --limit=2000 \
    --format=json \
    --freshness=4h > "${TEMP_DIR}/logs.json"

# Create Python analysis script
cat > "${TEMP_DIR}/analyze.py" << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Analyze Cloud Run Job execution in real-time"""

import json
import sys
from datetime import datetime, timezone
from collections import defaultdict
import re
import pytz

def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime"""
    return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

def format_duration(seconds):
    """Format seconds into human-readable duration"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def main():
    # Load execution metadata
    with open(sys.argv[1], 'r') as f:
        execution = json.load(f)

    # Load logs
    with open(sys.argv[2], 'r') as f:
        logs_data = json.load(f)

    # Parse execution details
    exec_name = execution['metadata']['name']
    start_time_str = execution['status'].get('startTime', '')
    completion_time_str = execution['status'].get('completionTime', '')

    if not start_time_str:
        print("Error: Execution has not started yet")
        sys.exit(1)

    start_time = parse_timestamp(start_time_str)

    # Convert to EST
    est = pytz.timezone('America/New_York')
    start_time_est = start_time.astimezone(est)

    # Calculate elapsed time
    if completion_time_str:
        end_time = parse_timestamp(completion_time_str)
        status = "COMPLETED"
    else:
        end_time = datetime.now(timezone.utc)
        status = "RUNNING"

    elapsed_seconds = (end_time - start_time).total_seconds()
    elapsed_minutes = elapsed_seconds / 60

    # Parse logs
    tickers_processed = set()
    delisted_tickers = set()
    errors = []
    api_calls = 0
    progress_updates = []
    last_ticker = None

    # API call patterns
    api_patterns = [
        'Fetching fundamentals for',
        'Fetching analyst',
        'Fetching volatility',
        'Fetching ticker details',
        'get_ticker_details',
        'get_stock_financials'
    ]

    for entry in logs_data:
        text = entry.get('textPayload', '')
        timestamp = entry.get('timestamp', '')

        # Track progress updates
        if 'Progress:' in text:
            progress_updates.append(text)

        # Track tickers being processed
        ticker_match = re.search(r'(?:Processing|Screening|Fetching.*for)\s+([A-Z]{1,5})(?:\s|:|$)', text)
        if ticker_match:
            ticker = ticker_match.group(1)
            tickers_processed.add(ticker)
            last_ticker = ticker

        # Track API calls
        if any(pattern in text for pattern in api_patterns):
            api_calls += 1

        # Track delisted/error tickers
        if 'possibly delisted' in text.lower() or 'no price data found' in text.lower():
            delisted_match = re.search(r'\$?([A-Z]{1,5})', text)
            if delisted_match:
                delisted_tickers.add(delisted_match.group(1))

        # Track errors
        if 'ERROR' in text or 'Error' in text or 'error' in text:
            if text not in [e['message'] for e in errors]:
                errors.append({
                    'message': text,
                    'timestamp': timestamp,
                    'count': 1
                })
            else:
                for e in errors:
                    if e['message'] == text:
                        e['count'] += 1

    # Calculate metrics
    unique_tickers = len(tickers_processed)
    tickers_per_minute = unique_tickers / elapsed_minutes if elapsed_minutes > 0 else 0
    api_calls_per_minute = api_calls / elapsed_minutes if elapsed_minutes > 0 else 0

    # Estimate total based on batch
    if 'batch-1' in exec_name:
        estimated_total = 1200  # A-D
        batch_name = "Batch 1 (A-D)"
    elif 'batch-2' in exec_name:
        estimated_total = 1200  # E-J
        batch_name = "Batch 2 (E-J)"
    elif 'batch-3' in exec_name:
        estimated_total = 1200  # K-N
        batch_name = "Batch 3 (K-N)"
    elif 'batch-4' in exec_name:
        estimated_total = 1200  # O-S
        batch_name = "Batch 4 (O-S)"
    elif 'batch-5' in exec_name:
        estimated_total = 1200  # T-Z
        batch_name = "Batch 5 (T-Z)"
    else:
        estimated_total = unique_tickers  # Unknown batch
        batch_name = "Unknown Batch"

    # Calculate estimates
    tickers_remaining = max(0, estimated_total - unique_tickers)
    minutes_remaining = tickers_remaining / tickers_per_minute if tickers_per_minute > 0 else 0

    # Determine if job is running efficiently
    efficiency_status = "UNKNOWN"
    efficiency_color = "yellow"

    if tickers_per_minute >= 8:
        efficiency_status = "EXCELLENT"
        efficiency_color = "green"
    elif tickers_per_minute >= 5:
        efficiency_status = "GOOD"
        efficiency_color = "green"
    elif tickers_per_minute >= 2:
        efficiency_status = "SLOW"
        efficiency_color = "yellow"
    else:
        efficiency_status = "VERY SLOW"
        efficiency_color = "red"

    # Print report
    print("\n" + "="*80)
    print("CLOUD RUN JOB AUDIT REPORT")
    print("="*80)
    print(f"Execution ID: {exec_name}")
    print(f"Batch: {batch_name}")
    print(f"Status: {status}")
    print("")

    print("⏱  TIMING")
    print("="*80)
    print(f"Start Time (EST):    {start_time_est.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
    print(f"Elapsed Time:        {format_duration(elapsed_seconds)}")
    if status == "RUNNING" and minutes_remaining > 0:
        print(f"Est. Remaining:      {format_duration(minutes_remaining * 60)}")
        total_est = elapsed_seconds + (minutes_remaining * 60)
        print(f"Est. Total Runtime:  {format_duration(total_est)}")
    print("")

    print("📊 PROGRESS")
    print("="*80)
    print(f"Stocks Processed:    {unique_tickers:,} / ~{estimated_total:,} ({unique_tickers/estimated_total*100:.1f}%)")
    print(f"Last Ticker:         {last_ticker or 'N/A'}")
    print(f"Tickers/Minute:      {tickers_per_minute:.2f} tickers/min")
    print(f"Efficiency:          {efficiency_status}")
    print("")

    print("🔌 API PERFORMANCE")
    print("="*80)
    print(f"Total API Calls:     {api_calls:,}")
    print(f"API Calls/Minute:    {api_calls_per_minute:.1f} calls/min")
    print(f"Calls per Ticker:    {api_calls/unique_tickers:.1f} calls/ticker" if unique_tickers > 0 else "Calls per Ticker:    N/A")

    # API rate limit guidance
    if api_calls_per_minute > 50:
        print(f"⚠️  WARNING: API rate ({api_calls_per_minute:.1f}/min) exceeds safe limit (50/min)")
    elif api_calls_per_minute > 45:
        print(f"⚠️  CAUTION: API rate ({api_calls_per_minute:.1f}/min) approaching limit")
    else:
        print(f"✓  API rate is within safe limits")
    print("")

    print("⚠️  ERRORS & ISSUES")
    print("="*80)
    print(f"Total Errors:        {len(errors)}")
    print(f"Delisted Tickers:    {len(delisted_tickers)}")

    if delisted_tickers:
        print(f"\nDelisted/Invalid Tickers ({len(delisted_tickers)}):")
        for ticker in sorted(delisted_tickers)[:20]:  # Show first 20
            print(f"  - {ticker}")
        if len(delisted_tickers) > 20:
            print(f"  ... and {len(delisted_tickers) - 20} more")

    if errors:
        print(f"\nTop Error Types:")
        sorted_errors = sorted(errors, key=lambda x: x['count'], reverse=True)
        for i, err in enumerate(sorted_errors[:5], 1):
            msg = err['message'][:100] + "..." if len(err['message']) > 100 else err['message']
            print(f"  {i}. [{err['count']}x] {msg}")

    print("\n" + "="*80)

    # Print recent progress updates
    if progress_updates:
        print("\n📈 RECENT PROGRESS UPDATES:")
        for update in progress_updates[-3:]:
            print(f"  {update}")

    # Recommendations
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)

    if efficiency_status in ["VERY SLOW", "SLOW"]:
        print("⚠️  Job is running slower than optimal.")
        print("   Consider:")
        print("   - Increasing worker count (currently 6)")
        print("   - Increasing rate limit if not hitting API limits")
        print("   - Checking for network/API latency issues")
    elif efficiency_status in ["GOOD", "EXCELLENT"]:
        print("✓  Job is running at good speed. Let it continue.")

    if api_calls_per_minute > 45:
        print("⚠️  API rate is high. Risk of rate limiting.")
        print("   Consider lowering rate limit or worker count.")

    if len(delisted_tickers) > 50:
        print(f"⚠️  High number of delisted tickers ({len(delisted_tickers)}).")
        print("   Run populate_delisted_blacklist.py to pre-filter next time.")

    print("\n" + "="*80)
    print("")

if __name__ == "__main__":
    main()
PYTHON_SCRIPT

# Run analysis
python3 "${TEMP_DIR}/analyze.py" "${TEMP_DIR}/execution.json" "${TEMP_DIR}/logs.json"

# Cleanup temp files (optional - keep for debugging)
# rm -rf "${TEMP_DIR}"

echo ""
echo -e "${BLUE}Note: Logs saved to ${TEMP_DIR}/${NC}"
echo -e "${BLUE}Run this script again to see updated progress.${NC}"
echo ""
