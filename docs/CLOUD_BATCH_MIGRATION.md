# Cloud Batch Migration Guide

## Overview

This guide details the migration from Cloud Run Jobs to Cloud Batch + Spot VMs for the daily screener batch jobs. The migration follows a phased approach to minimize risk and validate performance at each stage.

**Cost Savings**: $347.52/year (96.5% reduction)
**Migration Time**: 3-4 weeks
**Risk Level**: Low (phased rollout with dual-system validation)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Changes](#architecture-changes)
3. [Phase 1: Pilot (Batch 1)](#phase-1-pilot-batch-1)
4. [Phase 2: Expand (Batch 1-3)](#phase-2-expand-batch-1-3)
5. [Phase 3: Full Migration](#phase-3-full-migration)
6. [Phase 4: Cleanup](#phase-4-cleanup)
7. [Validation Criteria](#validation-criteria)
8. [Monitoring](#monitoring)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting the migration, ensure:

- [x] Cloud Run Jobs optimizations complete (1 vCPU, 1Gi, 3h timeout)
- [x] Terraform updated with new timeout/resource limits
- [ ] Enable Google Cloud Batch API:
  ```bash
  gcloud services enable batch.googleapis.com --project=sylvan-earth-477020-u6
  ```
- [ ] Service account has required permissions:
  - `roles/batch.jobsEditor`
  - `roles/compute.instanceAdmin.v1` (for Spot VMs)
  - `roles/iam.serviceAccountUser`
- [ ] Monitoring dashboards ready:
  - Cloud Batch job status
  - Firestore write metrics
  - Cost tracking dashboard

---

## Architecture Changes

### Key Differences

| Aspect | Cloud Run Jobs | Cloud Batch |
|--------|---------------|-------------|
| **Compute** | Serverless containers | Managed Spot VMs |
| **Cold Start** | ~10-30 seconds | ~2-3 minutes |
| **Cost** | $30/month | $1.04/month |
| **Billing** | Per-second | Per-hour (rounded up) |
| **Preemption** | None | 1-5% risk (auto-retry) |
| **Networking** | Automatic | Requires VPC config |

### What Stays the Same

✅ Docker images (no code changes)
✅ Environment variables
✅ Firestore access
✅ Cloud Scheduler triggers
✅ Logging format
✅ Same cron schedules

---

## Phase 1: Pilot (Batch 1)

**Goal**: Validate Cloud Batch works for one batch without disrupting production
**Duration**: Week 1 (5 business days)
**Risk**: Minimal (Cloud Run still running as backup)

### Steps

#### 1.1 Enable Cloud Batch API

```bash
gcloud services enable batch.googleapis.com --project=sylvan-earth-477020-u6
```

#### 1.2 Grant Service Account Permissions

```bash
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"

# Batch job editor
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"

# Compute instance admin (for Spot VMs)
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/compute.instanceAdmin.v1"
```

#### 1.3 Deploy Cloud Batch Infrastructure

Edit `terraform/environments/prod/batch_migration.tf`:

```terraform
# Uncomment the Phase 1 module block
module "batch_jobs_pilot" {
  source = "../../modules/batch_jobs"

  project_id              = var.project_id
  region                  = var.region
  scheduler_region        = var.scheduler_region
  environment             = var.environment
  service_account_email   = module.backend.service_account_email
  polygon_api_key_secret  = module.secrets.polygon_api_key_id
  docker_image            = var.batch_docker_image
  job_timeout_seconds     = 10800
  vm_machine_type         = "e2-medium"
  rate_limit_per_minute   = 58

  # Enable only batch-1 for pilot
  enable_batches = {
    batch-1 = true
    batch-2 = false
    batch-3 = false
    batch-4 = false
    batch-5 = false
  }
}
```

#### 1.4 Apply Terraform

```bash
cd terraform/environments/prod

# Preview changes
terraform plan

# Apply (creates Cloud Batch job + scheduler for batch-1)
terraform apply

# Verify resources created
terraform output batch_migration_status
```

#### 1.5 Validate Dual-System Operation

Both systems will now run in parallel:
- **Cloud Run batch-1**: 4:30 PM ET (existing)
- **Cloud Batch batch-1**: 4:30 PM ET (new)

Monitor both for 5 business days.

#### 1.6 Monitor Phase 1 (5 Days)

**Daily Checks:**

```bash
# Check Cloud Batch execution status
gcloud batch jobs list \
  --location=us-east5 \
  --filter="name:prod-regular-screeners-batch-1" \
  --limit=5

# Check Cloud Run execution status (existing)
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=5

# Compare results in Firestore
python3 backend/jobs/analyze_daily_runs.py
```

**Expected Results:**
- Cloud Batch saves to: `screeners/undiscovered/runs/2025-11-XX-batch-1`
- Cloud Run saves to: `screeners/undiscovered/runs/2025-11-XX-batch-1` (overwrites)
- Stock counts should match
- Runtime: Cloud Batch ~2-3 min slower (cold start)

### Phase 1 Validation Criteria

Before proceeding to Phase 2, verify:

- [ ] All 5 Cloud Batch runs completed successfully
- [ ] Firestore results match Cloud Run results (±5%)
- [ ] No Spot VM preemptions (or auto-retry worked)
- [ ] Logs appear in Cloud Logging correctly
- [ ] Runtime: 97-100 minutes (acceptable)
- [ ] Cost: <$0.20 per run vs $0.30 for Cloud Run

**Decision**: If all criteria pass → Proceed to Phase 2. If failures → Rollback (see [Rollback Procedures](#rollback-procedures))

---

## Phase 2: Expand (Batch 1-3)

**Goal**: Scale to 60% of workload
**Duration**: Week 2 (5 business days)
**Risk**: Low (validated in Phase 1)

### Steps

#### 2.1 Expand to Batches 2 and 3

Edit `terraform/environments/prod/batch_migration.tf`:

```terraform
# Update enable_batches
enable_batches = {
  batch-1 = true
  batch-2 = true
  batch-3 = true
  batch-4 = false
  batch-5 = false
}
```

#### 2.2 Apply Terraform

```bash
cd terraform/environments/prod
terraform apply
```

This creates:
- `prod-batch-regular-screeners-batch-2`
- `prod-batch-regular-screeners-batch-3`
- Associated Cloud Schedulers

#### 2.3 Monitor Phase 2 (5 Days)

**Daily Checks:**
```bash
# Check all 3 batches
for batch in 1 2 3; do
  echo "Batch $batch:"
  gcloud batch jobs list --location=us-east5 \
    --filter="name:prod-regular-screeners-batch-$batch" \
    --limit=1
done

# Compare results
python3 backend/jobs/analyze_daily_runs.py
```

### Phase 2 Validation Criteria

- [ ] All 3 batches running successfully for 5 days
- [ ] Firestore results consistent with Cloud Run
- [ ] No unusual Spot VM preemptions (<5% of runs)
- [ ] Cost tracking: ~$0.06/day (3 batches × $0.02)

**Decision**: If all criteria pass → Proceed to Phase 3

---

## Phase 3: Full Migration

**Goal**: Migrate all 5 batches to Cloud Batch
**Duration**: Week 3 (5 business days)
**Risk**: Low (60% validated in Phase 2)

### Steps

#### 3.1 Enable All Batches

Edit `terraform/environments/prod/batch_migration.tf`:

```terraform
# Enable all 5 batches
enable_batches = {
  batch-1 = true
  batch-2 = true
  batch-3 = true
  batch-4 = true
  batch-5 = true
}
```

#### 3.2 Apply Terraform

```bash
cd terraform/environments/prod
terraform apply
```

#### 3.3 Monitor Full System (5 Days)

```bash
# Daily health check
./scripts/analyze-batch-runs.sh

# Aggregated results
python3 backend/jobs/analyze_daily_runs.py
```

### Phase 3 Validation Criteria

- [ ] All 5 batches running successfully for 5 days
- [ ] Total ~4,960 stocks processed daily
- [ ] Firestore results match expected patterns
- [ ] Cost: ~$1.04/month (validate with billing dashboard)
- [ ] No operational issues

**Decision**: If all criteria pass → Proceed to Phase 4 (Cleanup)

---

## Phase 4: Cleanup

**Goal**: Decommission Cloud Run Jobs infrastructure
**Duration**: Week 4
**Risk**: Minimal (keep Cloud Run jobs for 7 days as backup)

### Steps

#### 4.1 Disable Cloud Run Schedulers (Keep Jobs)

Edit `terraform/modules/scheduled_jobs/main.tf`:

Comment out the Cloud Scheduler resources (lines 395-422):

```terraform
# TEMPORARILY DISABLED - Cloud Batch now handling these workloads
# resource "google_cloud_scheduler_job" "trigger_regular_screeners_batch" {
#   for_each = local.regular_batches
#   ...
# }
```

Apply:
```bash
cd terraform/environments/prod
terraform apply
```

**Result**: Cloud Run schedulers deleted, but jobs still exist (can be manually triggered if needed)

#### 4.2 Monitor Cloud Batch Only (7 Days)

Validate Cloud Batch runs smoothly without Cloud Run backup:

```bash
# Daily check
python3 backend/jobs/analyze_daily_runs.py

# No Cloud Run executions should appear
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=1
```

#### 4.3 Delete Cloud Run Jobs (After 7-Day Safety Window)

Edit `terraform/modules/scheduled_jobs/main.tf`:

Comment out the Cloud Run Job resources (lines 212-297):

```terraform
# DECOMMISSIONED - Migrated to Cloud Batch
# resource "google_cloud_run_v2_job" "regular_screeners_batch" {
#   for_each = local.regular_batches
#   ...
# }
```

Apply:
```bash
cd terraform/environments/prod
terraform apply
```

#### 4.4 Update Documentation

Update `CLAUDE.md` and `README.md`:
- Remove references to Cloud Run Jobs
- Add Cloud Batch architecture diagrams
- Update cost estimates ($12.48/year)
- Update operational procedures

---

## Validation Criteria

### Success Metrics (Per Phase)

| Metric | Target | How to Check |
|--------|--------|--------------|
| **Job Success Rate** | 100% (all runs complete) | `gcloud batch jobs list` |
| **Runtime** | 95-100 minutes | Check logs or execution times |
| **Firestore Results** | Match expected counts | `python3 backend/jobs/analyze_daily_runs.py` |
| **Spot Preemptions** | <5% of runs | Check Cloud Logging for preemption events |
| **Cost Per Run** | <$0.02 | Cloud Billing dashboard |
| **Data Integrity** | No missing stocks | Compare with previous day's results |

### Failure Conditions (Rollback Triggers)

- ❌ >10% job failure rate (2+ failures in 5 days)
- ❌ >10% Spot VM preemption rate
- ❌ Consistent data discrepancies (>5% difference)
- ❌ Runtime >120 minutes (25% slower than Cloud Run)
- ❌ Cost >$0.10 per run (higher than Cloud Run!)

---

## Monitoring

### Daily Monitoring Commands

```bash
# 1. Check job execution status
gcloud batch jobs list --location=us-east5 \
  --filter="name:prod-regular-screeners" \
  --limit=10

# 2. View recent job logs
gcloud logging read \
  'resource.type="batch_task" AND resource.labels.job_uid=~"prod-regular-screeners"' \
  --limit=50 \
  --format="table(timestamp, textPayload)"

# 3. Check Firestore results
python3 backend/jobs/analyze_daily_runs.py

# 4. Monitor costs (requires billing export)
# Check Cloud Billing dashboard:
# https://console.cloud.google.com/billing/
```

### Automated Monitoring (Recommended)

Create a Cloud Monitoring dashboard:

```bash
# Create alert for job failures
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="Cloud Batch Job Failures" \
  --condition-display-name="Job failed" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="batch.googleapis.com/Job" AND metric.type="batch.googleapis.com/job/failed_task_count"'
```

### Key Metrics to Track

1. **Job Completion Rate**: Should be 100% (5/5 batches daily)
2. **Average Runtime**: ~95-100 minutes per batch
3. **Spot Preemption Rate**: <5%
4. **Cost Per Day**: ~$0.052 (5 batches × $0.0104)
5. **Firestore Write Success**: 100%

---

## Rollback Procedures

### When to Rollback

Rollback immediately if:
- Critical job failures (>2 consecutive days)
- Data integrity issues (missing or incorrect results)
- Spot VM preemption rate >10%
- Operational burden too high

### Rollback Steps

#### 1. Disable Cloud Batch Schedulers

```bash
cd terraform/environments/prod

# Edit batch_migration.tf - comment out module block
# Then apply
terraform apply
```

This stops Cloud Batch jobs from triggering.

#### 2. Re-enable Cloud Run Schedulers

```bash
# Edit terraform/modules/scheduled_jobs/main.tf
# Uncomment Cloud Scheduler resources (lines 395-422)

cd terraform/environments/prod
terraform apply
```

#### 3. Verify Cloud Run Jobs Resume

```bash
# Check next scheduled run completes successfully
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=3
```

#### 4. Delete Cloud Batch Resources (Optional)

Once Cloud Run validated:

```bash
# Destroy Cloud Batch resources
terraform destroy -target=module.batch_jobs_pilot
```

---

## Troubleshooting

### Issue: Spot VM Preempted Mid-Job

**Symptoms**: Job fails after 30-60 minutes with preemption message

**Solution**: Cloud Batch auto-retries once. If persistent:
```bash
# Manually trigger retry
gcloud batch jobs submit <job-name> --location=us-east5
```

**Prevention**: Consider standard VMs for critical batches:
```terraform
provisioning_model = "STANDARD"  # Instead of "SPOT"
```

### Issue: Job Times Out After 3 Hours

**Symptoms**: Job killed at exactly 10,800 seconds

**Solution**: Increase timeout temporarily:
```terraform
job_timeout_seconds = 14400  # 4 hours
```

Then investigate why job is slow (API rate limit issues, network problems).

### Issue: Permission Denied Errors

**Symptoms**: `403 Forbidden` or `Permission denied` in logs

**Solution**: Verify service account permissions:
```bash
gcloud projects get-iam-policy sylvan-earth-477020-u6 \
  --flatten="bindings[].members" \
  --filter="bindings.members:prod-backend-sa@*"
```

Ensure roles:
- `roles/batch.jobsEditor`
- `roles/compute.instanceAdmin.v1`
- `roles/datastore.user`
- `roles/secretmanager.secretAccessor`

### Issue: Firestore Results Missing

**Symptoms**: `analyze_daily_runs.py` shows 0 results

**Possible Causes**:
1. Job failed silently (check logs)
2. Batch number mismatch (check BATCH_NUMBER env var)
3. Firestore permissions issue

**Solution**:
```bash
# Check logs for errors
gcloud logging read \
  'resource.type="batch_task" AND severity>=ERROR' \
  --limit=20

# Manually verify job completed
gcloud batch jobs describe <job-name> --location=us-east5
```

### Issue: Cost Higher Than Expected

**Symptoms**: Daily cost >$0.10 (should be ~$0.052)

**Possible Causes**:
1. Using standard VMs instead of Spot
2. Jobs running longer than expected
3. Multiple retry attempts

**Solution**:
```bash
# Check VM provisioning model
gcloud compute instances list --filter="name:batch-*"

# Verify Spot VMs being used (should show "SPOT" in description)
```

---

## Cost Tracking

### Expected Monthly Costs

| Month | Cloud Run (Old) | Cloud Batch (New) | Savings |
|-------|----------------|-------------------|---------|
| Month 1 (Phase 1) | $30.00 | $0.21 (1 batch) | $29.79 |
| Month 2 (Phase 2) | $30.00 | $0.62 (3 batches) | $29.38 |
| Month 3 (Phase 3) | $30.00 | $1.04 (5 batches) | $28.96 |
| Month 4+ | $0.00 (deleted) | $1.04 | $28.96/month |

**Annual Savings**: $347.52

### Validate Cost Savings

```bash
# Export billing data to BigQuery (if configured)
# Query for Cloud Batch costs:
SELECT
  DATE(usage_start_time) as date,
  service.description,
  SUM(cost) as daily_cost
FROM `<project>.billing.gcp_billing_export_v1_<billing_id>`
WHERE service.description LIKE '%Batch%'
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY date, service.description
ORDER BY date DESC
```

---

## Post-Migration Checklist

After completing all 4 phases:

- [ ] All 5 batches running on Cloud Batch
- [ ] Cloud Run schedulers disabled
- [ ] Cloud Run jobs deleted (after 7-day safety window)
- [ ] Documentation updated (CLAUDE.md, README.md)
- [ ] Monitoring dashboards updated for Cloud Batch
- [ ] Team trained on new operational procedures
- [ ] Rollback procedure tested and documented
- [ ] Cost savings validated (~$28.96/month)

---

## Next Steps After Migration

1. **Monitor for 1 Month**: Ensure stability before declaring success
2. **Optimize VM Type**: Test e2-small (cheaper) if CPU usage is low
3. **Implement Caching**: Add fundamentals caching for further speedup
4. **Scale to Smart Money**: Apply same migration to Smart Money screeners
5. **Document Learnings**: Update runbooks with lessons learned

---

## Support

If issues arise during migration:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review Cloud Batch logs: `gcloud logging read 'resource.type="batch_task"'`
3. Compare with Cloud Run baseline behavior
4. [Rollback](#rollback-procedures) if critical issues persist

**Emergency Rollback Contact**: Maintain access to re-enable Cloud Run schedulers

---

## References

- [Google Cloud Batch Documentation](https://cloud.google.com/batch/docs)
- [Spot VM Pricing](https://cloud.google.com/compute/docs/instances/spot)
- [Cloud Batch Best Practices](https://cloud.google.com/batch/docs/best-practices)
- [Terraform Cloud Batch Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/batch_job)
