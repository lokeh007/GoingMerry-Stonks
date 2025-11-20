# Cloud Batch Migration - Phase 1 Deployment Guide

## 📋 Overview

This guide provides step-by-step commands for deploying Phase 1 of the Cloud Batch migration. Phase 1 is a **pilot deployment** that enables **Batch 1 only** while keeping Cloud Run Jobs running as backup.

**Duration:** Week 1 (5 business days)
**Risk Level:** Minimal (Cloud Run continues as backup)
**Expected Cost:** ~$0.21 for the week vs $6.00 for Cloud Run
**Daily Time Commitment:** ~5 minutes/day for monitoring

---

## 🔧 Prerequisites Checklist

Before starting, verify:

- [ ] You have GCP project owner or editor permissions
- [ ] You have `gcloud` CLI installed and authenticated
- [ ] You're in the project directory: `/home/user/GoingMerry-Stonks`
- [ ] Terraform is installed (v1.0+)
- [ ] You have reviewed the changes made to Terraform files

---

## ✅ Terraform Fixes Applied

The following issues have been fixed and are ready for deployment:

### 1. Variable Name Correction
- **Issue:** `batch_migration.tf` referenced undefined variable `var.batch_docker_image`
- **Fix:** Changed to use existing `var.docker_image` variable (lines 31, 60, 89)
- **Impact:** Module now correctly references the Docker image for regular screeners

### 2. Enable Batches Filtering
- **Issue:** Module created all 5 batches regardless of `enable_batches` setting
- **Fix:** Added `local.enabled_batches` filter in module (main.tf:133-138)
- **Impact:** Module now respects the `enable_batches` variable for phased rollout

### 3. Updated For-Each Loops
- **Changed:** `google_batch_job` resource to use `local.enabled_batches`
- **Changed:** `google_cloud_scheduler_job` resource to use `local.enabled_batches`
- **Changed:** Output `batch_info` to use `local.enabled_batches`
- **Impact:** Only enabled batches are created and reported

---

## 🚀 Phase 1 Deployment Steps

### Step 1: Enable Cloud Batch API

```bash
# Enable the Cloud Batch API
gcloud services enable batch.googleapis.com \
  --project=sylvan-earth-477020-u6

# Verify API is enabled
gcloud services list --enabled \
  --project=sylvan-earth-477020-u6 \
  --filter="name:batch.googleapis.com"
```

**Expected Output:**
```
NAME                         TITLE
batch.googleapis.com         Cloud Batch API
```

---

### Step 2: Grant Service Account Permissions

```bash
# Set service account email
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"

# Grant Batch jobs editor role
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"

# Grant Compute instance admin role (for Spot VMs)
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/compute.instanceAdmin.v1"

# Verify permissions
gcloud projects get-iam-policy sylvan-earth-477020-u6 \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SA_EMAIL}" \
  --format="table(bindings.role)"
```

**Expected Roles:**
- `roles/batch.jobsEditor`
- `roles/compute.instanceAdmin.v1`
- `roles/datastore.user` (already exists)
- `roles/secretmanager.secretAccessor` (already exists)
- `roles/logging.logWriter` (already exists)

---

### Step 3: Uncomment Phase 1 Configuration

Edit `terraform/environments/prod/batch_migration.tf`:

```bash
# Open the file in your editor
# Uncomment lines 22-44 (the Phase 1 module block)
```

**Or use this command:**

```bash
cd /home/user/GoingMerry-Stonks

# Uncomment lines 22-44 (Phase 1 module block)
sed -i '22,44s/^# //' terraform/environments/prod/batch_migration.tf
```

**Verify the change:**
```bash
head -n 50 terraform/environments/prod/batch_migration.tf | tail -n 30
```

You should see the module block uncommented starting with:
```terraform
module "batch_jobs_pilot" {
  source = "../../modules/batch_jobs"
  ...
}
```

---

### Step 4: Terraform Plan (Preview Changes)

```bash
cd terraform/environments/prod

# Initialize Terraform (if not already done)
terraform init

# Preview the changes
terraform plan
```

**Expected Resources to be Created:**
```
Plan: 7 to add, 0 to change, 0 to destroy

Resources to be created:
  + google_batch_job.regular_screeners_batch["batch-1"]
  + google_cloud_scheduler_job.trigger_regular_screeners_batch["batch-1"]
  + google_project_iam_member.artifact_reader
  + google_project_iam_member.batch_job_runner
  + google_project_iam_member.firestore_user
  + google_project_iam_member.log_writer
  + google_project_iam_member.secret_accessor
```

**⚠️ STOP HERE if you see:**
- More than 1 batch being created (should only be batch-1)
- Any resources being destroyed
- Any errors or warnings

---

### Step 5: Apply Terraform (Deploy Phase 1)

```bash
# Apply the changes
terraform apply

# Review the plan again, then type: yes
```

**Expected Output:**
```
Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

Outputs:
batch_migration_status = {
  "batch-1" = {
    batch_number = 1
    job_name = "prod-regular-screeners-batch-1"
    schedule = "30 16 * * 1-5"
    scheduler = "prod-trigger-batch-regular-screeners-batch-1"
    time = "4:30 PM ET"
  }
}
```

---

### Step 6: Verify Deployment

```bash
# Verify Cloud Batch job created
gcloud batch jobs list \
  --location=us-east5 \
  --project=sylvan-earth-477020-u6

# Verify Cloud Scheduler created
gcloud scheduler jobs list \
  --location=us-east1 \
  --project=sylvan-earth-477020-u6 \
  --filter="name:prod-trigger-batch"

# Check service account permissions
gcloud projects get-iam-policy sylvan-earth-477020-u6 \
  --flatten="bindings[].members" \
  --filter="bindings.members:prod-backend-sa@*" \
  --format="table(bindings.role)"
```

**Expected:**
- 1 Cloud Batch job: `prod-regular-screeners-batch-1`
- 1 Cloud Scheduler: `prod-trigger-batch-regular-screeners-batch-1`
- Service account has all required roles

---

## 📊 Monitoring Phase 1 (5 Business Days)

### Daily Monitoring Checklist

Run these commands **once per day** after the scheduled run time (after 6:30 PM ET):

#### 1. Check Cloud Batch Execution

```bash
# View recent Cloud Batch job executions
gcloud batch jobs list \
  --location=us-east5 \
  --filter="name:prod-regular-screeners-batch-1" \
  --limit=5

# View logs from today's run
gcloud logging read \
  'resource.type="batch_task"
   AND resource.labels.job_uid=~"prod-regular-screeners-batch-1"
   AND timestamp>="'$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%S)'"' \
  --limit=50 \
  --format="table(timestamp, severity, textPayload)"
```

**Expected Status:** `SUCCEEDED` (not `FAILED`)

#### 2. Check Cloud Run Execution (Existing System)

```bash
# View recent Cloud Run job executions
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=5
```

**Expected Status:** Both systems should be running successfully

#### 3. Check Firestore Results

```bash
# Check Firestore for today's results
python3 backend/jobs/analyze_daily_runs.py $(date +%Y-%m-%d)
```

**Expected Output:**
```
Date: 2025-11-20
Batch 1 (Cloud Batch): 992 stocks
Batch 1 (Cloud Run): 992 stocks (overwrites Cloud Batch)
Status: ✅ Both systems successful
```

**Note:** Cloud Run and Cloud Batch both write to the same Firestore path, so the last one to complete will overwrite. This is expected during dual-system operation.

#### 4. Monitor Costs

```bash
# View costs in Cloud Console
# Go to: https://console.cloud.google.com/billing
# Filter by: Service = "Cloud Batch API"
# Date range: Last 7 days
```

**Expected Cost:** ~$0.02 per run (vs $0.30 for Cloud Run)

---

## 📈 Phase 1 Validation Criteria

After **5 business days** of monitoring, verify these criteria before proceeding to Phase 2:

| Criterion | Target | How to Check | Status |
|-----------|--------|--------------|--------|
| **Cloud Batch Success Rate** | 5/5 runs successful | `gcloud batch jobs list` | [ ] |
| **Firestore Results** | ~992 stocks per batch | `analyze_daily_runs.py` | [ ] |
| **Data Accuracy** | Match Cloud Run (±5%) | Compare Firestore results | [ ] |
| **Spot VM Preemptions** | 0 or auto-recovered | Check logs for "preempted" | [ ] |
| **Runtime** | 95-100 minutes | Check execution times | [ ] |
| **Cost** | <$0.02 per run | Cloud Billing dashboard | [ ] |
| **No Errors** | No critical errors | Check logs for severity>=ERROR | [ ] |

### Validation Commands

```bash
# Count successful runs (should be 5 after week 1)
gcloud batch jobs list \
  --location=us-east5 \
  --filter="name:prod-regular-screeners-batch-1 AND status:SUCCEEDED" \
  --limit=10 | grep -c "SUCCEEDED"

# Check for any errors
gcloud logging read \
  'resource.type="batch_task"
   AND resource.labels.job_uid=~"prod-regular"
   AND severity>=ERROR' \
  --limit=20

# View all execution times
gcloud batch jobs list \
  --location=us-east5 \
  --filter="name:prod-regular-screeners-batch-1" \
  --format="table(name, status.runDuration, createTime, status.state)"
```

---

## 🔄 Rollback Procedure (If Needed)

If Phase 1 encounters issues, rollback immediately:

### When to Rollback
- 2+ consecutive Cloud Batch failures
- Data integrity issues (missing stocks, incorrect results)
- Spot VM preemption rate >10%
- Any critical blocking issues

### Rollback Steps

```bash
cd terraform/environments/prod

# Comment out the Phase 1 module block
sed -i '22,44s/^/# /' batch_migration.tf

# Apply to remove Cloud Batch resources
terraform apply

# Verify Cloud Run continues working
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=3
```

**Rollback Time:** ~5 minutes
**Impact:** Zero (Cloud Run continues uninterrupted)

---

## ✅ Phase 1 Completion Checklist

After 5 business days, verify all criteria:

- [ ] All 5 Cloud Batch runs completed successfully
- [ ] Firestore results match Cloud Run results (±5%)
- [ ] No Spot VM preemptions (or auto-retry worked)
- [ ] Logs show no critical errors
- [ ] Runtime averages 95-100 minutes
- [ ] Cost is <$0.02 per run (~$0.10 for week)
- [ ] Team is comfortable with monitoring procedures

**✅ If all criteria pass:** Proceed to Phase 2 (expand to batches 1-3)
**❌ If any criteria fail:** Review logs, troubleshoot, or rollback

---

## 📞 Troubleshooting

### Issue: "Permission denied" errors

**Solution:**
```bash
# Re-grant permissions
SA_EMAIL="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/batch.jobsEditor"
```

### Issue: Spot VM preempted

**Solution:**
- Cloud Batch auto-retries once
- Check if retry succeeded: `gcloud batch jobs list --filter="name:prod-regular-screeners-batch-1"`
- If persistent, we can switch to standard VMs in Phase 2

### Issue: Job timeout after 3 hours

**Solution:**
- This indicates a performance issue
- Check API rate limits and network connectivity
- Job should complete in ~95-100 minutes

### Issue: Firestore results missing

**Solution:**
```bash
# Check if job actually completed
gcloud batch jobs describe prod-regular-screeners-batch-1 \
  --location=us-east5

# Check logs for Firestore write errors
gcloud logging read \
  'resource.type="batch_task"
   AND textPayload=~"Firestore"
   AND severity>=ERROR' \
  --limit=20
```

---

## 🎯 Next Steps

After Phase 1 validation (5 business days):

1. **Review Results:** Analyze all metrics and logs
2. **Decision Point:**
   - ✅ Success → Proceed to Phase 2 (batches 1-3)
   - ❌ Issues → Rollback and investigate
3. **Phase 2 Prep:** Review `docs/CLOUD_BATCH_MIGRATION.md` Section 5

---

## 📚 References

- **Full Migration Guide:** `docs/CLOUD_BATCH_MIGRATION.md`
- **Quick Reference:** `docs/CLOUD_BATCH_QUICK_REFERENCE.md`
- **Terraform Module:** `terraform/modules/batch_jobs/main.tf`
- **Cloud Batch Docs:** https://cloud.google.com/batch/docs

---

## 📝 Notes

- Both Cloud Run and Cloud Batch will run simultaneously during Phase 1
- This is intentional - we're validating Cloud Batch before disabling Cloud Run
- The last system to complete will overwrite Firestore (expected behavior)
- Zero risk to production - Cloud Run continues as backup
- You can manually trigger a test run before waiting for the schedule:
  ```bash
  gcloud scheduler jobs run prod-trigger-batch-regular-screeners-batch-1 \
    --location=us-east1
  ```

---

**Good luck with Phase 1! 🚀**

Remember: This is a low-risk pilot. Take your time, monitor carefully, and rollback if needed.
