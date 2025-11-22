# Cloud Batch Migration - Quick Start Guide

Quick reference for executing the Cloud Batch migration plan.

**Full Plan**: See [CLOUD_BATCH_MIGRATION_PLAN.md](./CLOUD_BATCH_MIGRATION_PLAN.md)

---

## Prerequisites

✅ Service account has required permissions:
```bash
# Verify permissions
gcloud projects get-iam-policy sylvan-earth-477020-u6 \
  --flatten="bindings[].members" \
  --filter="bindings.members:prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"

# Should include:
# - roles/batch.agentReporter
# - roles/artifactregistry.reader
# - roles/datastore.user
# - roles/secretmanager.secretAccessor
```

---

## Phase 1: Pilot (Week 1)

### Day 1: Deploy Batch 1

```bash
# 1. Deploy Cloud Batch job for regular batch 1
./scripts/deploy-cloud-batch-prod.sh 1 regular

# 2. Create Cloud Scheduler
./scripts/create-batch-schedulers.sh 1

# 3. Keep existing Cloud Run scheduler active (parallel running)
gcloud scheduler jobs describe prod-regular-screeners-batch-1 --location=us-east1
```

### Day 2-5: Monitor Daily

```bash
# Daily validation
./scripts/validate-migration.sh

# Check specific job
gcloud batch jobs describe prod-batch-regular-screeners-batch-1-cb --location=us-east5

# View logs
gcloud logging read 'labels.job_uid=~"prod-batch-regular-screeners-batch-1"' --limit=50

# Analyze results
python3 backend/jobs/analyze_daily_runs.py
```

### Day 5: Go/No-Go Decision

**GO Criteria**:
- ✅ 5/5 successful runs
- ✅ Runtime < 110 minutes
- ✅ Result counts within ±10% of Cloud Run
- ✅ Zero Spot preemptions (or successful retry)

**If GO**:
```bash
# Disable Cloud Run scheduler
gcloud scheduler jobs pause prod-regular-screeners-batch-1 --location=us-east1

# Rename Cloud Batch scheduler (remove "-cb")
# (Manual: Delete old, recreate without suffix)

# Archive Cloud Run job (don't delete yet)
gcloud run jobs describe prod-regular-screeners-batch-1 --region=us-east5 \
  --format=yaml > archive/cloud-run/regular-batch-1.yaml
```

---

## Phase 2: Expansion (Week 2-3)

### Deploy Batches 2-3

```bash
# Deploy jobs
./scripts/deploy-cloud-batch-prod.sh 2 regular
./scripts/deploy-cloud-batch-prod.sh 3 regular

# Create schedulers
./scripts/create-batch-schedulers.sh 2

# Monitor for 5 days
./scripts/validate-migration.sh
```

### Go/No-Go (Day 11)

**GO Criteria**:
- ✅ 15/15 successful runs (5 days × 3 batches)
- ✅ No Firestore conflicts
- ✅ Frontend performance unchanged

**If GO**:
```bash
# Pause Cloud Run schedulers for batches 1-3
for i in 1 2 3; do
  gcloud scheduler jobs pause prod-regular-screeners-batch-$i --location=us-east1
done
```

---

## Phase 3: Full Migration (Week 3-4)

### Deploy All 10 Batches

```bash
# Deploy remaining regular batches
./scripts/deploy-cloud-batch-prod.sh 4 regular
./scripts/deploy-cloud-batch-prod.sh 5 regular

# Deploy Smart Money batches
for i in 1 2 3 4 5; do
  ./scripts/deploy-cloud-batch-prod.sh $i smart-money
done

# Create all schedulers
./scripts/create-batch-schedulers.sh 3

# Monitor for 7 days
./scripts/validate-migration.sh
./scripts/monitor-daily-batch.sh
```

### Go/No-Go (Day 18)

**GO Criteria**:
- ✅ 70/70 successful runs (7 days × 10 batches)
- ✅ Daily cost < $0.125
- ✅ Zero operational issues

**If GO**:
```bash
# Pause all Cloud Run schedulers
for i in 1 2 3 4 5; do
  gcloud scheduler jobs pause prod-regular-screeners-batch-$i --location=us-east1
  gcloud scheduler jobs pause prod-smart-money-batch-$i --location=us-east1
done

# Wait 14 days grace period before decommission
```

---

## Phase 4: Decommission (Week 7)

### After 14-day Grace Period

```bash
# 1. Archive Cloud Run configurations
mkdir -p archive/cloud-run

for i in 1 2 3 4 5; do
  gcloud run jobs describe prod-regular-screeners-batch-$i --region=us-east5 \
    --format=yaml > archive/cloud-run/regular-batch-$i.yaml

  gcloud run jobs describe prod-smart-money-batch-$i --region=us-east5 \
    --format=yaml > archive/cloud-run/smart-money-batch-$i.yaml
done

git add archive/cloud-run/
git commit -m "Archive Cloud Run job definitions before decommission"

# 2. Delete Cloud Run schedulers
for i in 1 2 3 4 5; do
  gcloud scheduler jobs delete prod-regular-screeners-batch-$i --location=us-east1 --quiet
  gcloud scheduler jobs delete prod-smart-money-batch-$i --location=us-east1 --quiet
done

# 3. Delete Cloud Run jobs
for i in 1 2 3 4 5; do
  gcloud run jobs delete prod-regular-screeners-batch-$i --region=us-east5 --quiet
  gcloud run jobs delete prod-smart-money-batch-$i --region=us-east5 --quiet
done

# 4. Update documentation
# - CLAUDE.md: Remove Cloud Run Jobs from architecture
# - README.md: Update deployment instructions
# - DEPLOYMENT_STATUS.md: Change to Cloud Batch
```

---

## Emergency Rollback

If Cloud Batch fails at any phase:

```bash
# 1. Pause Cloud Batch schedulers
gcloud scheduler jobs pause prod-regular-screeners-batch-1-cb --location=us-east1
# (pause all affected batches)

# 2. Resume Cloud Run schedulers
gcloud scheduler jobs resume prod-regular-screeners-batch-1 --location=us-east1
# (resume all affected batches)

# 3. Trigger manual Cloud Run execution if schedule missed
gcloud run jobs execute prod-regular-screeners-batch-1 --region=us-east5

# 4. Create incident report and investigate
```

---

## Daily Operations

### Monitor Jobs

```bash
# Daily report (automated)
./scripts/monitor-daily-batch.sh

# Check specific batch
gcloud batch jobs describe prod-batch-regular-screeners-batch-1 --location=us-east5

# View recent logs
gcloud logging read 'resource.type="batch.googleapis.com/Job"' --limit=50
```

### Trigger Manual Run

```bash
# Via scheduler
gcloud scheduler jobs run prod-regular-screeners-batch-1-cb --location=us-east1

# Direct deployment
./scripts/deploy-cloud-batch-prod.sh 1 regular
```

### Check Results

```bash
# Analyze Firestore data
python3 backend/jobs/analyze_daily_runs.py

# View specific batch results
# Firestore Console: screeners/{screener}/runs/2025-11-21-batch-1
```

---

## Cost Tracking

### Current State (Cloud Run)
- **Daily**: $0.44
- **Monthly**: $13.20

### Target State (Cloud Batch)
- **Daily**: $0.125
- **Monthly**: $3.75
- **Savings**: 71.6% ($9.45/month)

### Verify Cost
```bash
# Check Billing in GCP Console
# https://console.cloud.google.com/billing

# Export to BigQuery and query:
SELECT
  DATE(usage_start_time) as date,
  service.description,
  SUM(cost) as total_cost
FROM `sylvan-earth-477020-u6.billing_export.gcp_billing_export_*`
WHERE service.description LIKE '%Batch%'
GROUP BY date, service.description
ORDER BY date DESC
LIMIT 30;
```

---

## Troubleshooting

### Job Failed

```bash
# Get failure reason
gcloud batch jobs describe JOB_NAME --location=us-east5 --format="value(status.statusEvents)"

# View logs
gcloud logging read 'labels.job_uid="JOB_UID"' --limit=100

# Common issues:
# - Image pull error: Check artifactregistry.reader permission
# - Timeout: Increase maxRunDuration in job config
# - Spot preemption: Check maxRetryCount=1 is configured
```

### Results Not in Firestore

```bash
# Check job succeeded
gcloud batch jobs list --filter="state=SUCCEEDED" --limit=10

# Check Firestore directly
# https://console.cloud.google.com/firestore/data/panel/screeners

# Verify document path format: screeners/{screener}/runs/2025-11-21-batch-1
```

### High Runtime

```bash
# Check VM specs
gcloud batch jobs describe JOB_NAME --location=us-east5 \
  --format="value(allocationPolicy.instances.policy)"

# Consider:
# - Increase CPU: cpuMilli from 1000 to 2000
# - Increase RAM: memoryMib from 1024 to 2048
# - Use standard VMs instead of Spot (higher cost)
```

---

## Success Metrics

Track these KPIs:

| Metric | Target | Alert |
|--------|--------|-------|
| Success Rate | 100% | < 95% |
| Runtime (Regular) | < 100m | > 110m |
| Runtime (Smart Money) | < 120m | > 135m |
| Cost per Run | $0.011-0.014 | > $0.020 |
| Spot Preemptions | 0 | > 1/week |

---

## Additional Resources

- **Full Migration Plan**: [CLOUD_BATCH_MIGRATION_PLAN.md](./CLOUD_BATCH_MIGRATION_PLAN.md)
- **Manual Deployment Guide**: [CLOUD_BATCH_MANUAL_DEPLOY.md](./CLOUD_BATCH_MANUAL_DEPLOY.md)
- **Project Architecture**: [../CLAUDE.md](../CLAUDE.md)
- **GCP Batch Documentation**: https://cloud.google.com/batch/docs

---

**Questions?** Review the full migration plan or create an issue in the repo.

**Last Updated**: 2025-11-21
