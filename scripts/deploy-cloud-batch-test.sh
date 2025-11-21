#!/bin/bash
#
# Quick Deploy Script for Cloud Batch Testing
#
# Usage: ./scripts/deploy-cloud-batch-test.sh [batch_number]
#   batch_number: 1-5 (default: 1 for testing)

set -e

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
DOCKER_IMAGE="us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"

BATCH_NUM=${1:-1}

if [ "$BATCH_NUM" -lt 1 ] || [ "$BATCH_NUM" -gt 5 ]; then
  echo "Error: Batch number must be between 1 and 5"
  exit 1
fi

echo "================================================================================"
echo "Cloud Batch Deployment - Batch $BATCH_NUM"
echo "================================================================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Docker Image: $DOCKER_IMAGE"
echo ""

# Create job definition
echo "Creating job definition..."
cat > /tmp/batch-job-${BATCH_NUM}.json <<EOF
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
                "RATE_LIMIT_PER_MINUTE": "58"
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
    "deployment": "manual-test"
  }
}
EOF

echo "✓ Job definition created: /tmp/batch-job-${BATCH_NUM}.json"
echo ""

# Submit job
echo "Submitting Cloud Batch job..."
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-${BATCH_NUM} \
  --location=$REGION \
  --config=/tmp/batch-job-${BATCH_NUM}.json

if [ $? -eq 0 ]; then
  echo ""
  echo "================================================================================"
  echo "✓ Batch $BATCH_NUM submitted successfully!"
  echo "================================================================================"
  echo ""
  echo "Monitor with:"
  echo "  gcloud batch jobs describe prod-batch-test-regular-screeners-batch-${BATCH_NUM} --location=$REGION"
  echo ""
  echo "View logs:"
  echo "  gcloud logging read 'resource.type=\"batch.googleapis.com/Job\" AND resource.labels.job_uid=~\"prod-batch-test-regular-screeners-batch-${BATCH_NUM}\"' --limit=100"
  echo ""
  echo "Check results:"
  echo "  python3 backend/jobs/analyze_daily_runs.py"
  echo ""
else
  echo ""
  echo "✗ Job submission failed!"
  exit 1
fi
