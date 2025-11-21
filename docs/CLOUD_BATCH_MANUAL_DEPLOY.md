# Cloud Batch Manual Deployment Guide

## Overview

This guide shows how to deploy Cloud Batch jobs using `gcloud` commands to test them alongside your existing Cloud Run jobs before making any Terraform changes.

**Goal**: Run both systems in parallel to validate performance and cost savings.

---

## Prerequisites

```bash
# 1. Enable Cloud Batch API
gcloud services enable batch.googleapis.com --project=sylvan-earth-477020-u6

# 2. Set environment variables
export PROJECT_ID="sylvan-earth-477020-u6"
export REGION="us-east5"
export SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
export DOCKER_IMAGE="us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"

# 3. Grant permissions to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/compute.instanceAdmin.v1"
```

---

## Step 1: Create Cloud Batch Job Definitions

### Batch 1 (A-D, ~992 stocks)

Create a job definition file:

```bash
cat > /tmp/batch-job-1.json <<'EOF'
{
  "taskGroups": [
    {
      "taskSpec": {
        "runnables": [
          {
            "container": {
              "imageUri": "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest",
              "commands": [
                "python",
                "/app/jobs/run_daily_screeners.py"
              ],
              "environment": {
                "variables": {
                  "BATCH_NUMBER": "1",
                  "GCP_PROJECT_ID": "sylvan-earth-477020-u6",
                  "ENVIRONMENT": "prod",
                  "PYTHONUNBUFFERED": "1",
                  "RATE_LIMIT_PER_MINUTE": "58"
                },
                "secretVariables": {
                  "POLYGON_API_KEY": "projects/sylvan-earth-477020-u6/secrets/prod-polygon-api-key/versions/latest"
                }
              }
            }
          }
        ],
        "computeResource": {
          "cpuMilli": 1000,
          "memoryMib": 1024
        },
        "maxRunDuration": "10800s"
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
    "serviceAccount": {
      "email": "prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
    }
  },
  "logsPolicy": {
    "destination": "CLOUD_LOGGING"
  },
  "labels": {
    "environment": "prod",
    "batch": "1",
    "deployment": "manual-test"
  }
}
EOF
```

### Create the Job

```bash
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-1 \
  --location=$REGION \
  --config=/tmp/batch-job-1.json
```

---

## Step 2: Create Jobs for All 5 Batches

Instead of manually creating 5 files, use this script:

```bash
cat > /tmp/create-batch-jobs.sh <<'SCRIPT'
#!/bin/bash

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
DOCKER_IMAGE="us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"

for batch_num in 1 2 3 4 5; do
  echo "Creating Cloud Batch job for batch ${batch_num}..."

  cat > /tmp/batch-job-${batch_num}.json <<EOF
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
              ],
              "environment": {
                "variables": {
                  "BATCH_NUMBER": "${batch_num}",
                  "GCP_PROJECT_ID": "${PROJECT_ID}",
                  "ENVIRONMENT": "prod",
                  "PYTHONUNBUFFERED": "1",
                  "RATE_LIMIT_PER_MINUTE": "58"
                }
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
    "serviceAccount": {
      "email": "${SA_EMAIL}"
    }
  },
  "logsPolicy": {
    "destination": "CLOUD_LOGGING"
  },
  "labels": {
    "environment": "prod",
    "batch": "${batch_num}",
    "deployment": "manual-test"
  }
}
EOF

  echo "Job definition created: /tmp/batch-job-${batch_num}.json"
done

echo ""
echo "Job definitions created. Review them, then run the jobs manually."
SCRIPT

chmod +x /tmp/create-batch-jobs.sh
/tmp/create-batch-jobs.sh
```

---

## Step 3: Manual Job Execution (Testing Phase)

### Run a Single Batch (Test First)

Start with Batch 1 to validate:

```bash
# Submit the job
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --config=/tmp/batch-job-1.json

# Monitor the job
gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5

# View logs
gcloud batch jobs logs prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5
```

### Check Job Status

```bash
# List all batch jobs
gcloud batch jobs list --location=us-east5

# Get detailed status
gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --format="table(name, state, createTime, statusEvents)"
```

### View Logs in Cloud Logging

```bash
# View logs (alternative method)
gcloud logging read \
  'resource.type="batch.googleapis.com/Job" AND resource.labels.job_uid=~"prod-batch-test"' \
  --limit=100 \
  --format="table(timestamp, textPayload)"
```

---

## Step 4: Comparison Testing Plan

### Phase 1: Single Batch Test (Day 1)

**Goal**: Validate Cloud Batch batch-1 works correctly

```bash
# At 4:30 PM ET, manually trigger Cloud Batch batch-1
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --config=/tmp/batch-job-1.json

# Cloud Run batch-1 will also run automatically at 4:30 PM ET (existing scheduler)

# Compare results the next morning
python3 backend/jobs/analyze_daily_runs.py
```

**Validation Criteria**:
- [ ] Cloud Batch job completes successfully
- [ ] Runtime: 95-105 minutes (2-10 min slower than Cloud Run)
- [ ] Firestore results match Cloud Run batch-1
- [ ] No Spot VM preemption (or auto-retry worked)

### Phase 2: All Batches Test (Day 2-5)

If Phase 1 passes, manually trigger all 5 batches:

```bash
# Trigger all 5 batches at their scheduled times
# Use this script to automate:

cat > /tmp/trigger-all-batches.sh <<'SCRIPT'
#!/bin/bash

REGION="us-east5"

for batch_num in 1 2 3 4 5; do
  echo "Submitting batch ${batch_num}..."

  gcloud batch jobs submit prod-batch-test-regular-screeners-batch-${batch_num} \
    --location=$REGION \
    --config=/tmp/batch-job-${batch_num}.json

  if [ $? -eq 0 ]; then
    echo "✓ Batch ${batch_num} submitted successfully"
  else
    echo "✗ Batch ${batch_num} submission failed"
  fi

  echo ""
done

echo "All batches submitted. Monitor with:"
echo "  gcloud batch jobs list --location=$REGION"
SCRIPT

chmod +x /tmp/trigger-all-batches.sh
```

**Manual Trigger Times**:
```bash
# Batch 1: 4:30 PM ET
./tmp/trigger-all-batches.sh  # Just batch 1 at 4:30 PM

# Batch 2: 6:00 PM ET
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-2 \
  --location=us-east5 --config=/tmp/batch-job-2.json

# Batch 3: 7:30 PM ET
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-3 \
  --location=us-east5 --config=/tmp/batch-job-3.json

# Batch 4: 9:00 PM ET
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-4 \
  --location=us-east5 --config=/tmp/batch-job-4.json

# Batch 5: 10:30 PM ET
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-5 \
  --location=us-east5 --config=/tmp/batch-job-5.json
```

---

## Step 5: Monitoring & Validation

### Daily Health Check

```bash
# Check all jobs
gcloud batch jobs list --location=us-east5 --filter="labels.deployment=manual-test"

# View today's results
python3 backend/jobs/analyze_daily_runs.py

# Compare Cloud Run vs Cloud Batch
echo "Cloud Run Jobs:"
gcloud run jobs executions list --job=prod-regular-screeners-batch-1 --region=us-east5 --limit=1

echo ""
echo "Cloud Batch Jobs:"
gcloud batch jobs list --location=us-east5 --filter="name:prod-batch-test" --limit=5
```

### Cost Tracking

```bash
# View billing for Cloud Batch
# Go to: https://console.cloud.google.com/billing

# Filter by:
# - Service: "Batch API"
# - Date range: Last 7 days
# - Expected cost: ~$0.01-0.02 per batch run
```

---

## Step 6: Comparison Results Template

Track results in a spreadsheet or document:

```
Date: 2025-11-20

Batch 1 (A-D):
  Cloud Run:
    - Start: 4:30 PM ET
    - End: 6:07 PM ET
    - Runtime: 97 minutes
    - Stocks Found: 50 (Undiscovered), 6 (Coiled Spring)
    - Cost: $0.30

  Cloud Batch:
    - Start: 4:30 PM ET
    - End: 6:10 PM ET
    - Runtime: 100 minutes (3 min slower - cold start)
    - Stocks Found: 50 (Undiscovered), 6 (Coiled Spring)
    - Spot Preempted: No
    - Cost: $0.01
    - Savings: $0.29 (96.7%)

Batch 2 (E-J):
  [Same format]

...
```

---

## Automated Scheduling (After Validation)

Once validated (5-7 days of successful runs), automate with Cloud Scheduler:

### Create Cloud Scheduler Jobs

```bash
# Scheduler for Batch 1
gcloud scheduler jobs create http prod-batch-scheduler-regular-batch-1 \
  --location=us-east1 \
  --schedule="30 16 * * 1-5" \
  --time-zone="America/New_York" \
  --uri="https://batch.googleapis.com/v1/projects/sylvan-earth-477020-u6/locations/us-east5/jobs/prod-batch-test-regular-screeners-batch-1:run" \
  --http-method=POST \
  --oauth-service-account-email=$SA_EMAIL \
  --description="Cloud Batch trigger for regular screeners batch 1 (4:30 PM ET)"

# Repeat for batches 2-5 with appropriate schedules
```

**Scheduler Times**:
- Batch 1: `30 16 * * 1-5` (4:30 PM ET)
- Batch 2: `0 18 * * 1-5` (6:00 PM ET)
- Batch 3: `30 19 * * 1-5` (7:30 PM ET)
- Batch 4: `0 21 * * 1-5` (9:00 PM ET)
- Batch 5: `30 22 * * 1-5` (10:30 PM ET)

---

## Rollback Procedure

If Cloud Batch doesn't work as expected:

### 1. Stop Cloud Batch Jobs

```bash
# Delete all test batch jobs
for batch_num in 1 2 3 4 5; do
  gcloud batch jobs delete prod-batch-test-regular-screeners-batch-${batch_num} \
    --location=us-east5 \
    --quiet
done
```

### 2. Verify Cloud Run Still Running

```bash
# Confirm Cloud Run jobs are still executing on schedule
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=5

# All 5 batches should show recent executions
```

### 3. No Terraform Changes Needed

Since we deployed manually, no Terraform rollback required. Just delete the Cloud Batch jobs.

---

## Troubleshooting

### Issue: Job Fails with "Permission Denied"

**Solution**: Grant required permissions

```bash
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"

# Batch API access
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"

# VM management
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/compute.instanceAdmin.v1"

# Firestore access (should already have this)
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

# Secret access (should already have this)
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Logging
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter"
```

### Issue: Spot VM Preempted

**Check**:
```bash
gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --format="value(statusEvents)"
```

**Solution**: Cloud Batch auto-retries once. If persistent, switch to standard VMs:

```json
{
  "policy": {
    "machineType": "e2-medium",
    "provisioningModel": "STANDARD"  // Instead of "SPOT"
  }
}
```

### Issue: Job Takes Too Long

**Check Current Runtime**:
```bash
gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --format="value(createTime, endTime)"
```

**Expected**: 97-105 minutes (similar to Cloud Run)
**If Slower**: Check VM startup time in logs (should be ~2-3 min)

### Issue: Missing Firestore Results

**Check**:
```bash
# View job logs
gcloud batch jobs logs prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 | grep -E "Saved to Firestore|ERROR"

# Check Firestore directly
python3 backend/jobs/analyze_daily_runs.py
```

---

## Cost Validation

### Expected Costs (Per Day)

| System | Cost per Run | Daily (5 batches) | Monthly (20 days) |
|--------|--------------|-------------------|-------------------|
| **Cloud Run (Current)** | $0.15 | $0.75 | $15.00 |
| **Cloud Batch (Spot VMs)** | $0.01 | $0.05 | $1.04 |
| **Daily Savings** | -$0.14 | -$0.70 | **-$13.96** |

### Verify Actual Costs

```bash
# After 1 week of testing, check actual costs:
# 1. Go to: https://console.cloud.google.com/billing
# 2. Filter by SKU: "Spot Preemptible E2 Instance Core"
# 3. Date range: Last 7 days
# 4. Expected: ~$0.35-0.40 total (7 days × $0.05/day)
```

---

## Next Steps

### After 5-7 Days of Successful Testing

1. **Validate Results**:
   - [ ] All 5 batches completed successfully
   - [ ] Firestore results match Cloud Run
   - [ ] Cost savings validated (~96%)
   - [ ] No operational issues

2. **Automate Scheduling**:
   - Create Cloud Scheduler jobs (see "Automated Scheduling" above)
   - Test schedulers for 2-3 days

3. **Decommission Cloud Run**:
   - Disable Cloud Run schedulers in Terraform
   - Keep Cloud Run jobs for 1 week as backup
   - Delete Cloud Run jobs after validation period

4. **Update Terraform** (Optional):
   - Document manual Cloud Batch deployment
   - Or create custom Terraform module using null_resource + gcloud

---

## Summary

**Manual Deployment Advantages**:
- ✅ No Terraform changes required
- ✅ Easy to test and validate
- ✅ Quick rollback (just delete jobs)
- ✅ Learn Cloud Batch before committing to IaC

**Total Time Investment**:
- Setup: 30 minutes
- Daily monitoring: 5 minutes
- Validation period: 5-7 days

**Expected Savings**: $167.52/year (96.5% reduction on compute costs)

---

## Quick Start Commands

```bash
# 1. Enable API and grant permissions
gcloud services enable batch.googleapis.com --project=sylvan-earth-477020-u6

SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"

# 2. Create job definitions
/tmp/create-batch-jobs.sh

# 3. Test batch 1
gcloud batch jobs submit prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5 \
  --config=/tmp/batch-job-1.json

# 4. Monitor
gcloud batch jobs describe prod-batch-test-regular-screeners-batch-1 \
  --location=us-east5

# 5. Check results
python3 backend/jobs/analyze_daily_runs.py
```

Good luck with the testing! 🚀
