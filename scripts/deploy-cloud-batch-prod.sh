#!/bin/bash
#
# Production Cloud Batch Deployment Script
#
# Usage: ./scripts/deploy-cloud-batch-prod.sh [batch_number] [screener_type]
#   batch_number: 1-5 (required)
#   screener_type: regular|smart-money (default: regular)
#
# Examples:
#   ./scripts/deploy-cloud-batch-prod.sh 1           # Deploy regular batch 1
#   ./scripts/deploy-cloud-batch-prod.sh 2 smart-money  # Deploy smart money batch 2

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
DOCKER_IMAGE="us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"

BATCH_NUM=${1}
SCREENER_TYPE=${2:-regular}

# Validate inputs
if [ -z "$BATCH_NUM" ]; then
  echo "Error: batch_number is required"
  echo "Usage: $0 [batch_number] [screener_type]"
  exit 1
fi

if [ "$BATCH_NUM" -lt 1 ] || [ "$BATCH_NUM" -gt 5 ]; then
  echo "Error: Batch number must be between 1 and 5"
  exit 1
fi

if [ "$SCREENER_TYPE" != "regular" ] && [ "$SCREENER_TYPE" != "smart-money" ]; then
  echo "Error: screener_type must be 'regular' or 'smart-money'"
  exit 1
fi

# Set job name based on screener type
if [ "$SCREENER_TYPE" = "smart-money" ]; then
  JOB_NAME="prod-batch-smart-money-screeners-batch-${BATCH_NUM}"
  RATE_LIMIT="45"  # Smart money uses 45 req/min
else
  JOB_NAME="prod-batch-regular-screeners-batch-${BATCH_NUM}"
  RATE_LIMIT="58"  # Regular uses 58 req/min
fi

echo "================================================================================"
echo "Cloud Batch Production Deployment"
echo "================================================================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Screener Type: $SCREENER_TYPE"
echo "Batch Number: $BATCH_NUM"
echo "Job Name: $JOB_NAME"
echo "Docker Image: $DOCKER_IMAGE"
echo "Rate Limit: $RATE_LIMIT req/min"
echo ""

# Create job definition
echo "Creating job definition..."
cat > /tmp/batch-job-${SCREENER_TYPE}-${BATCH_NUM}.json <<EOF
{
  "taskGroups": [
    {
      "taskSpec": {
        "runnables": [
          {
            "container": {
              "imageUri": "${DOCKER_IMAGE}",
              "commands": [
                "python",
                "/app/jobs/run_daily_screeners.py"
              ]
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
          }
        ],
        "computeResource": {
          "cpuMilli": 1000,
          "memoryMib": 1024
        },
        "maxRunDuration": "10800s",
        "maxRetryCount": 1
      },
      "taskCount": 1
    }
  ],
  "allocationPolicy": {
    "instances": [
      {
        "policy": {
          "machineType": "e2-medium",
          "provisioningModel": "SPOT"
        }
      }
    ],
    "network": {
      "networkInterfaces": [
        {
          "network": "global/networks/default",
          "noExternalIpAddress": false
        }
      ]
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
    "deployment": "production"
  }
}
EOF

echo "✓ Job definition created: /tmp/batch-job-${SCREENER_TYPE}-${BATCH_NUM}.json"
echo ""

# Submit job
echo "Submitting Cloud Batch job..."
gcloud batch jobs submit ${JOB_NAME} \
  --location=$REGION \
  --config=/tmp/batch-job-${SCREENER_TYPE}-${BATCH_NUM}.json

if [ $? -eq 0 ]; then
  echo ""
  echo "================================================================================"
  echo "✓ ${SCREENER_TYPE} Batch ${BATCH_NUM} submitted successfully!"
  echo "================================================================================"
  echo ""
  echo "Monitor with:"
  echo "  gcloud batch jobs describe ${JOB_NAME} --location=$REGION"
  echo ""
  echo "View logs:"
  echo "  gcloud logging read 'resource.type=\"batch.googleapis.com/Job\" AND labels.job_uid=~\"${JOB_NAME}\"' --limit=100"
  echo ""
  echo "Check results:"
  echo "  python3 backend/jobs/analyze_daily_runs.py"
  echo ""
else
  echo ""
  echo "✗ Job submission failed!"
  exit 1
fi
