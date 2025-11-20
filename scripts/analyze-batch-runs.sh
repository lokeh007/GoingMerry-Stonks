#!/bin/bash
#
# Quick Batch Job Analysis
#
# Analyzes all 5 regular screener batch jobs from yesterday (or specified date)
# Shows: runtime, errors, stocks found per screener
#
# Usage:
#   ./scripts/analyze-batch-runs.sh              # Yesterday's runs
#   ./scripts/analyze-batch-runs.sh 2025-11-17   # Specific date

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"

# Get date (default: yesterday)
if [ -z "$1" ]; then
    # Yesterday in YYYY-MM-DD format
    DATE=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null)
else
    DATE=$1
fi

echo "================================================================================"
echo "BATCH JOB ANALYSIS - Regular Screeners"
echo "================================================================================"
echo "Date: $DATE"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo "Analyzing 5 batches (A-D, E-J, K-N, O-S, T-Z)..."
echo ""

# Function to analyze a single batch
analyze_batch() {
    local batch_num=$1
    local batch_label=$2
    local job_name="prod-regular-screeners-batch-${batch_num}"

    echo "================================================================================"
    echo "BATCH ${batch_num}: ${batch_label}"
    echo "================================================================================"

    # Get most recent execution from the date
    execution_id=$(gcloud run jobs executions list \
        --job=$job_name \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="value(metadata.name)" \
        --filter="metadata.creationTimestamp.date('%Y-%m-%d')='${DATE}'" \
        --limit=1 2>/dev/null || echo "")

    if [ -z "$execution_id" ]; then
        echo "⚠️  No execution found for $DATE"
        echo ""
        return
    fi

    echo "Execution ID: $execution_id"

    # Get execution details
    exec_info=$(gcloud run jobs executions describe $execution_id \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="value(status.startTime,status.completionTime,status.succeededCount,status.failedCount)" 2>/dev/null || echo "")

    if [ -z "$exec_info" ]; then
        echo "❌ Could not fetch execution details"
        echo ""
        return
    fi

    # Parse execution info
    start_time=$(echo "$exec_info" | cut -f1)
    end_time=$(echo "$exec_info" | cut -f2)
    succeeded=$(echo "$exec_info" | cut -f3)
    failed=$(echo "$exec_info" | cut -f4)

    # Calculate duration
    if [ -n "$start_time" ] && [ -n "$end_time" ]; then
        start_epoch=$(date -d "$start_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$start_time" +%s 2>/dev/null)
        end_epoch=$(date -d "$end_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$end_time" +%s 2>/dev/null)
        duration_sec=$((end_epoch - start_epoch))
        duration_min=$((duration_sec / 60))
        duration_sec_remainder=$((duration_sec % 60))

        echo "Status: ✅ COMPLETED"
        echo "Runtime: ${duration_min}m ${duration_sec_remainder}s"
    else
        echo "Status: 🔄 RUNNING or FAILED"
    fi

    # Get logs for screening results
    echo ""
    echo "Screening Results (Batch ${batch_num}):"

    # Try to get screening completion logs with increased limit
    screening_logs=$(gcloud logging read \
        "resource.labels.job_name=${job_name} AND labels.\"run.googleapis.com/execution_name\"=${execution_id}" \
        --limit=500 \
        --format="value(textPayload)" \
        --project=$PROJECT_ID 2>/dev/null | \
        grep -E "✓ Undiscovered:|✓ Coiled Spring:|⚠ Not found|✗ Failed|Total execution time|Saved to Firestore" | \
        tail -15)

    if [ -n "$screening_logs" ]; then
        echo "$screening_logs"
    else
        # Fallback: try different log format or newer logs
        echo "  Fetching from alternative log source..."
        gcloud logging read \
            "resource.labels.job_name=${job_name} AND labels.\"run.googleapis.com/execution_name\"=${execution_id} AND textPayload:\"stocks passed\"" \
            --limit=50 \
            --format="value(textPayload)" \
            --project=$PROJECT_ID 2>/dev/null | \
            grep -E "Undiscovered|Coiled Spring|Not found|Failed" || echo "  ⚠️  Logs not available (may be expired or still indexing)"
        echo "  💡 Use Python script for reliable results: python3 backend/jobs/analyze_daily_runs.py $DATE"
    fi

    echo ""
    echo "Error Summary:"

    # Count errors in logs
    error_count=$(gcloud logging read \
        "resource.labels.job_name=${job_name} AND labels.\"run.googleapis.com/execution_name\"=${execution_id} AND severity>=ERROR" \
        --limit=100 \
        --format="value(textPayload)" \
        --project=$PROJECT_ID 2>/dev/null | wc -l || echo "0")

    if [ "$error_count" -gt 0 ]; then
        echo "  ⚠️  Found $error_count error log entries"
        echo ""
        echo "  Top errors:"
        gcloud logging read \
            "resource.labels.job_name=${job_name} AND labels.\"run.googleapis.com/execution_name\"=${execution_id} AND severity>=ERROR" \
            --limit=5 \
            --format="value(textPayload)" \
            --project=$PROJECT_ID 2>/dev/null | head -5
    else
        echo "  ✅ No errors detected"
    fi

    echo ""
}

# Analyze all 5 batches
analyze_batch 1 "A to CURB (~992 stocks)"
analyze_batch 2 "CURV to GRNJ (~992 stocks)"
analyze_batch 3 "GRNT to MPU (~992 stocks)"
analyze_batch 4 "MPV to SFGV (~992 stocks)"
analyze_batch 5 "SFL to ZWS (~992 stocks)"

echo "================================================================================"
echo "SUMMARY COMPLETE"
echo "================================================================================"
echo ""
echo "📊 For aggregated screening results across all batches, use:"
echo "  python3 backend/jobs/analyze_daily_runs.py $DATE"
echo ""
echo "This Python script queries Firestore directly for more reliable results."
echo ""
echo "================================================================================"
echo "OTHER USEFUL COMMANDS"
echo "================================================================================"
echo ""
echo "For detailed logs of a specific batch, run:"
echo "  ./scripts/monitor-batch-job.sh prod-regular-screeners-batch-X-<execution-id>"
echo ""
echo "For Firestore screening results, check:"
echo "  https://console.cloud.google.com/firestore/databases/-default-/data/panel/screeners;namespace=/"
echo ""
