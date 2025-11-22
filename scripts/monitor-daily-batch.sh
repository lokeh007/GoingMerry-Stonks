#!/bin/bash
#
# Daily Cloud Batch Monitoring Report
#
# Usage: ./scripts/monitor-daily-batch.sh [date]
#   date: YYYY-MM-DD (default: yesterday)
#
# Run via cron: 0 11 * * * cd /path/to/project && ./scripts/monitor-daily-batch.sh

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
DATE=${1:-$(TZ=America/New_York date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)}

echo "================================================================================"
echo "Daily Batch Report - $DATE"
echo "================================================================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Summary counters
TOTAL_JOBS=0
SUCCESS_JOBS=0
FAILED_JOBS=0
RUNNING_JOBS=0
TOTAL_RUNTIME=0
TOTAL_COST=0.0

echo "📊 Job Status"
echo "--------------------------------------------------------------------------------"

# Check all batch jobs
for TYPE in "regular" "smart-money"; do
  echo ""
  echo "$(echo $TYPE | tr '[:lower:]' '[:upper:]') SCREENERS:"

  for BATCH_NUM in 1 2 3 4 5; do
    if [ "$TYPE" = "smart-money" ]; then
      JOB_PREFIX="prod-batch-smart-money-screeners-batch-${BATCH_NUM}"
      EXPECTED_COST=0.014
    else
      JOB_PREFIX="prod-batch-regular-screeners-batch-${BATCH_NUM}"
      EXPECTED_COST=0.011
    fi

    # Find job created on this date
    JOB=$(gcloud batch jobs list \
      --location=$REGION \
      --filter="name:${JOB_PREFIX} AND createTime>=${DATE}T00:00:00 AND createTime<=${DATE}T23:59:59" \
      --format="value(name)" \
      --limit=1 \
      2>/dev/null)

    if [ -n "$JOB" ]; then
      TOTAL_JOBS=$((TOTAL_JOBS + 1))

      # Get job details
      STATUS=$(gcloud batch jobs describe $JOB --location=$REGION --format="value(status.state)" 2>/dev/null)
      RUNTIME_SEC=$(gcloud batch jobs describe $JOB --location=$REGION --format="value(status.runDuration)" 2>/dev/null | sed 's/s//')

      if [ -z "$RUNTIME_SEC" ]; then
        RUNTIME_SEC=0
      fi

      RUNTIME_MIN=$(echo "scale=1; $RUNTIME_SEC / 60" | bc)
      TOTAL_RUNTIME=$((TOTAL_RUNTIME + RUNTIME_SEC))

      if [ "$STATUS" = "SUCCEEDED" ]; then
        echo "  ✅ Batch $BATCH_NUM: SUCCEEDED (${RUNTIME_MIN}m, \$${EXPECTED_COST})"
        SUCCESS_JOBS=$((SUCCESS_JOBS + 1))
        TOTAL_COST=$(echo "$TOTAL_COST + $EXPECTED_COST" | bc)
      elif [ "$STATUS" = "FAILED" ]; then
        echo "  ❌ Batch $BATCH_NUM: FAILED (${RUNTIME_MIN}m)"
        FAILED_JOBS=$((FAILED_JOBS + 1))
      elif [ "$STATUS" = "RUNNING" ]; then
        echo "  ⏳ Batch $BATCH_NUM: RUNNING (${RUNTIME_MIN}m so far)"
        RUNNING_JOBS=$((RUNNING_JOBS + 1))
      else
        echo "  ⚠️  Batch $BATCH_NUM: $STATUS"
      fi
    else
      echo "  ➖ Batch $BATCH_NUM: Not found"
    fi
  done
done

echo ""
echo "--------------------------------------------------------------------------------"
echo "Summary:"
echo "  Total Jobs: $TOTAL_JOBS"
echo "  Succeeded: $SUCCESS_JOBS"
echo "  Failed: $FAILED_JOBS"
echo "  Running: $RUNNING_JOBS"

TOTAL_RUNTIME_MIN=$(echo "scale=1; $TOTAL_RUNTIME / 60" | bc)
TOTAL_RUNTIME_HR=$(echo "scale=2; $TOTAL_RUNTIME / 3600" | bc)
echo "  Total Runtime: ${TOTAL_RUNTIME_MIN}m (${TOTAL_RUNTIME_HR}h)"
echo "  Estimated Cost: \$${TOTAL_COST}"
echo ""

# Firestore Results Analysis
echo "📊 Firestore Results (Last 2 Days)"
echo "--------------------------------------------------------------------------------"
python3 backend/jobs/analyze_daily_runs.py 2>&1 | tail -50

echo ""

# Performance Summary
echo "📈 Performance Metrics"
echo "--------------------------------------------------------------------------------"

if [ $SUCCESS_JOBS -gt 0 ]; then
  AVG_RUNTIME=$(echo "scale=1; $TOTAL_RUNTIME / $SUCCESS_JOBS / 60" | bc)
  AVG_COST=$(echo "scale=4; $TOTAL_COST / $SUCCESS_JOBS" | bc)
  SUCCESS_RATE=$(echo "scale=1; $SUCCESS_JOBS * 100 / $TOTAL_JOBS" | bc)

  echo "  Average Runtime: ${AVG_RUNTIME}m per job"
  echo "  Average Cost: \$${AVG_COST} per job"
  echo "  Success Rate: ${SUCCESS_RATE}%"

  # SLA checks
  if [ $(echo "$AVG_RUNTIME > 110" | bc) -eq 1 ]; then
    echo "  ⚠️  WARNING: Average runtime exceeds 110m SLA!"
  fi

  if [ $(echo "$SUCCESS_RATE < 95" | bc) -eq 1 ]; then
    echo "  ⚠️  WARNING: Success rate below 95% target!"
  fi
fi

echo ""

# Recent Failures
if [ $FAILED_JOBS -gt 0 ]; then
  echo "❌ Recent Failures (last 3 days)"
  echo "--------------------------------------------------------------------------------"

  SINCE_DATE=$(TZ=America/New_York date -d "3 days ago" +%Y-%m-%d 2>/dev/null || date -v-3d +%Y-%m-%d)

  gcloud batch jobs list \
    --location=$REGION \
    --filter="status.state=FAILED AND createTime>=$SINCE_DATE" \
    --format="table(name,status.state,createTime,status.runDuration)" \
    2>/dev/null || echo "  No failures found"

  echo ""
fi

# Exit code based on results
if [ $FAILED_JOBS -gt 0 ]; then
  echo "⚠️  ALERT: $FAILED_JOBS job(s) failed today!"
  exit 1
elif [ $SUCCESS_JOBS -eq 10 ]; then
  echo "✅ All jobs completed successfully!"
  exit 0
else
  echo "ℹ️  Some jobs may still be running or scheduled."
  exit 0
fi
