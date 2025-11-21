#!/bin/bash
#
# Monitor Cloud Batch Jobs
#
# Usage: ./scripts/monitor-cloud-batch.sh

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"

echo "================================================================================"
echo "Cloud Batch Job Status"
echo "================================================================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# List all test batch jobs
echo "Active Jobs:"
echo "------------"
gcloud batch jobs list \
  --location=$REGION \
  --filter="labels.deployment=manual-test" \
  --format="table(name, state, createTime, runDuration)" \
  2>/dev/null || echo "No jobs found"

echo ""
echo "================================================================================"
echo "Job Details"
echo "================================================================================"
echo ""

# Get details for each batch
for batch_num in 1 2 3 4 5; do
  job_name="prod-batch-test-regular-screeners-batch-${batch_num}"
  
  # Check if job exists
  if gcloud batch jobs describe $job_name --location=$REGION &>/dev/null; then
    echo "Batch $batch_num:"
    
    state=$(gcloud batch jobs describe $job_name --location=$REGION --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    create_time=$(gcloud batch jobs describe $job_name --location=$REGION --format="value(createTime)" 2>/dev/null || echo "N/A")
    
    echo "  Status: $state"
    echo "  Created: $create_time"
    
    # If running or completed, show duration
    if [ "$state" == "SUCCEEDED" ] || [ "$state" == "RUNNING" ]; then
      duration=$(gcloud batch jobs describe $job_name --location=$REGION --format="value(runDuration)" 2>/dev/null || echo "N/A")
      echo "  Duration: $duration"
    fi
    
    echo ""
  fi
done

echo "================================================================================"
echo "Quick Commands"
echo "================================================================================"
echo ""
echo "View detailed status for a specific batch:"
echo "  gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 --location=$REGION"
echo ""
echo "View logs for a specific batch:"
echo "  gcloud logging read 'resource.type=\"batch.googleapis.com/Job\" AND resource.labels.job_uid=~\"prod-batch-test-regular-screeners-batch-1\"' --limit=100"
echo ""
echo "Check Firestore results:"
echo "  python3 backend/jobs/analyze_daily_runs.py"
echo ""
echo "Compare with Cloud Run:"
echo "  gcloud run jobs executions list --job=prod-regular-screeners-batch-1 --region=us-east5 --limit=3"
echo ""
