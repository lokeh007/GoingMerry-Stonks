#!/bin/bash
#
# Migration Validation Script
# Checks all Cloud Batch jobs and compares with Cloud Run results
#
# Usage: ./scripts/validate-migration.sh [date]
#   date: YYYY-MM-DD (default: today)

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
DATE=${1:-$(TZ=America/New_York date +%Y-%m-%d)}

echo "================================================================================"
echo "Cloud Batch Migration Validation - $DATE"
echo "================================================================================"
echo ""

# Check Cloud Batch jobs
echo "📊 Cloud Batch Job Status"
echo "--------------------------------------------------------------------------------"

SUCCESS_COUNT=0
FAILED_COUNT=0
RUNNING_COUNT=0

for TYPE in "regular" "smart-money"; do
  for BATCH_NUM in 1 2 3 4 5; do
    if [ "$TYPE" = "smart-money" ]; then
      JOB_NAME="prod-batch-smart-money-screeners-batch-${BATCH_NUM}"
    else
      JOB_NAME="prod-batch-regular-screeners-batch-${BATCH_NUM}"
    fi

    # Check if job exists and get its status
    STATUS=$(gcloud batch jobs list \
      --location=$REGION \
      --filter="name:$JOB_NAME AND createTime>$DATE" \
      --format="value(status.state)" \
      2>/dev/null | head -1)

    if [ -n "$STATUS" ]; then
      RUNTIME=$(gcloud batch jobs list \
        --location=$REGION \
        --filter="name:$JOB_NAME AND createTime>$DATE" \
        --format="value(status.runDuration)" \
        2>/dev/null | head -1)

      RUNTIME_MIN=$(echo "$RUNTIME" | sed 's/s//' | awk '{print int($1/60)}')

      if [ "$STATUS" = "SUCCEEDED" ]; then
        echo "✅ $TYPE Batch $BATCH_NUM: SUCCEEDED (${RUNTIME_MIN}m)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      elif [ "$STATUS" = "FAILED" ]; then
        echo "❌ $TYPE Batch $BATCH_NUM: FAILED"
        FAILED_COUNT=$((FAILED_COUNT + 1))
      elif [ "$STATUS" = "RUNNING" ]; then
        echo "⏳ $TYPE Batch $BATCH_NUM: RUNNING (${RUNTIME_MIN}m)"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
      else
        echo "⚠️  $TYPE Batch $BATCH_NUM: $STATUS"
      fi
    else
      echo "➖ $TYPE Batch $BATCH_NUM: Not found"
    fi
  done
done

echo ""
echo "Summary: ✅ $SUCCESS_COUNT succeeded | ❌ $FAILED_COUNT failed | ⏳ $RUNNING_COUNT running"
echo ""

# Check Firestore results
echo "📊 Firestore Results Analysis"
echo "--------------------------------------------------------------------------------"
python3 backend/jobs/analyze_daily_runs.py 2>/dev/null || echo "Error analyzing Firestore results"

echo ""

# Cost estimate
echo "💰 Cost Estimate"
echo "--------------------------------------------------------------------------------"
REGULAR_COST=$(echo "scale=3; $SUCCESS_COUNT * 0.011" | bc)
echo "Cloud Batch: \$$REGULAR_COST (${SUCCESS_COUNT} jobs × \$0.011)"
echo "Cloud Run (equivalent): \$0.44 (10 jobs × \$0.044 avg)"
echo ""

# Check for failures
if [ $FAILED_COUNT -gt 0 ]; then
  echo "⚠️  WARNING: $FAILED_COUNT job(s) failed!"
  echo ""
  echo "To investigate failures:"
  echo "  gcloud batch jobs list --location=$REGION --filter='status.state=FAILED'"
  echo ""
  exit 1
fi

if [ $SUCCESS_COUNT -eq 10 ]; then
  echo "✅ All 10 batch jobs succeeded!"
  exit 0
elif [ $RUNNING_COUNT -gt 0 ]; then
  echo "⏳ $RUNNING_COUNT job(s) still running. Check back later."
  exit 0
else
  echo "⚠️  Some jobs have not run yet."
  exit 0
fi
