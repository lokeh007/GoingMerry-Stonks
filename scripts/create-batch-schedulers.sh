#!/bin/bash
#
# Create Cloud Schedulers for Cloud Batch Jobs
#
# Usage: ./scripts/create-batch-schedulers.sh [phase]
#   phase: 1|2|3 (default: 1)
#     Phase 1: Batch 1 only (pilot)
#     Phase 2: Batches 1-3 (expansion)
#     Phase 3: All 10 batches (full migration)

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
SCHEDULER_REGION="us-east1"
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
DOCKER_IMAGE="us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"

PHASE=${1:-1}

if [ "$PHASE" -lt 1 ] || [ "$PHASE" -gt 3 ]; then
  echo "Error: Phase must be 1, 2, or 3"
  exit 1
fi

echo "================================================================================"
echo "Creating Cloud Schedulers - Phase $PHASE"
echo "================================================================================"
echo ""

create_scheduler() {
  local BATCH_NUM=$1
  local SCREENER_TYPE=$2
  local SCHEDULE=$3
  local RATE_LIMIT=$4

  if [ "$SCREENER_TYPE" = "smart-money" ]; then
    JOB_NAME="prod-batch-smart-money-screeners-batch-${BATCH_NUM}-cb"
    SCHEDULER_NAME="prod-smart-money-batch-${BATCH_NUM}-cb"
  else
    JOB_NAME="prod-batch-regular-screeners-batch-${BATCH_NUM}-cb"
    SCHEDULER_NAME="prod-regular-screeners-batch-${BATCH_NUM}-cb"
  fi

  echo "Creating scheduler: $SCHEDULER_NAME"
  echo "  Schedule: $SCHEDULE (America/New_York)"
  echo "  Job: $JOB_NAME"

  # Create job config file
  cat > /tmp/scheduler-${SCREENER_TYPE}-${BATCH_NUM}.json <<EOF
{
  "taskGroups": [{
    "taskSpec": {
      "runnables": [{
        "container": {
          "imageUri": "${DOCKER_IMAGE}",
          "commands": ["python", "/app/jobs/run_daily_screeners.py"]
        },
        "environment": {
          "variables": {
            "BATCH_NUMBER": "${BATCH_NUM}",
            "GCP_PROJECT_ID": "${PROJECT_ID}",
            "ENVIRONMENT": "prod",
            "PYTHONUNBUFFERED": "1",
            "RATE_LIMIT_PER_MINUTE": "${RATE_LIMIT}",
            "SCREENER_TYPE": "${SCREENER_TYPE}"
          }
        }
      }],
      "computeResource": {
        "cpuMilli": 1000,
        "memoryMib": 1024
      },
      "maxRunDuration": "10800s",
      "maxRetryCount": 1
    },
    "taskCount": 1
  }],
  "allocationPolicy": {
    "instances": [{
      "policy": {
        "machineType": "e2-medium",
        "provisioningModel": "SPOT"
      }
    }],
    "network": {
      "networkInterfaces": [{
        "network": "global/networks/default",
        "noExternalIpAddress": false
      }]
    },
    "serviceAccount": {
      "email": "${SA_EMAIL}"
    }
  },
  "logsPolicy": {
    "destination": "CLOUD_LOGGING"
  },
  "labels": {
    "environment": "prod",
    "batch": "${BATCH_NUM}",
    "screener-type": "${SCREENER_TYPE}",
    "deployment": "scheduled"
  }
}
EOF

  # Create Cloud Scheduler job
  gcloud scheduler jobs create http $SCHEDULER_NAME \
    --location=$SCHEDULER_REGION \
    --schedule="$SCHEDULE" \
    --time-zone="America/New_York" \
    --uri="https://batch.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/jobs" \
    --http-method=POST \
    --message-body-from-file=/tmp/scheduler-${SCREENER_TYPE}-${BATCH_NUM}.json \
    --headers="Content-Type=application/json" \
    --oauth-service-account-email="${SA_EMAIL}" \
    2>/dev/null || echo "  ⚠️  Scheduler may already exist"

  echo "  ✓ Created"
  echo ""
}

# Phase 1: Regular Batch 1 only
if [ "$PHASE" -eq 1 ]; then
  echo "Phase 1: Creating scheduler for Regular Batch 1 (pilot)"
  echo ""
  create_scheduler 1 "regular" "30 16 * * 1-5" "58"
fi

# Phase 2: Regular Batches 1-3
if [ "$PHASE" -eq 2 ]; then
  echo "Phase 2: Creating schedulers for Regular Batches 1-3 (expansion)"
  echo ""
  create_scheduler 1 "regular" "30 16 * * 1-5" "58"
  create_scheduler 2 "regular" "0 18 * * 1-5" "58"
  create_scheduler 3 "regular" "30 19 * * 1-5" "58"
fi

# Phase 3: All 10 batches
if [ "$PHASE" -eq 3 ]; then
  echo "Phase 3: Creating schedulers for all 10 batches (full migration)"
  echo ""

  # Regular screeners (5 batches)
  create_scheduler 1 "regular" "30 16 * * 1-5" "58"
  create_scheduler 2 "regular" "0 18 * * 1-5" "58"
  create_scheduler 3 "regular" "30 19 * * 1-5" "58"
  create_scheduler 4 "regular" "0 21 * * 1-5" "58"
  create_scheduler 5 "regular" "30 22 * * 1-5" "58"

  # Smart Money screeners (5 batches)
  create_scheduler 1 "smart-money" "0 0 * * 2-6" "45"
  create_scheduler 2 "smart-money" "0 2 * * 2-6" "45"
  create_scheduler 3 "smart-money" "0 4 * * 2-6" "45"
  create_scheduler 4 "smart-money" "0 6 * * 2-6" "45"
  create_scheduler 5 "smart-money" "0 8 * * 2-6" "45"
fi

echo "================================================================================"
echo "✓ Schedulers created successfully!"
echo "================================================================================"
echo ""
echo "View schedulers:"
echo "  gcloud scheduler jobs list --location=$SCHEDULER_REGION"
echo ""
echo "Trigger manual run:"
echo "  gcloud scheduler jobs run prod-regular-screeners-batch-1-cb --location=$SCHEDULER_REGION"
echo ""
