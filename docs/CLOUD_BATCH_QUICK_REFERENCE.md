# Cloud Batch Migration - Quick Reference

## 🚀 Migration Phases

| Phase | Duration | Batches | Risk | Rollback Time |
|-------|----------|---------|------|---------------|
| **Phase 1: Pilot** | Week 1 | Batch 1 only | Minimal | Instant |
| **Phase 2: Expand** | Week 2 | Batches 1-3 | Low | 5 minutes |
| **Phase 3: Full** | Week 3 | All 5 batches | Low | 10 minutes |
| **Phase 4: Cleanup** | Week 4 | Decommission Cloud Run | Minimal | 30 minutes |

---

## 📋 Daily Checklist (During Migration)

```bash
# 1. Check job status
gcloud batch jobs list --location=us-east5 --limit=5

# 2. Verify results
python3 backend/jobs/analyze_daily_runs.py

# 3. Compare costs (view billing dashboard)
# Expected: ~$0.01-0.02 per batch run
```

---

## ⚡ Quick Commands

### View Job Status
```bash
gcloud batch jobs list --location=us-east5 \
  --filter="name:prod-regular-screeners"
```

### View Job Logs
```bash
gcloud logging read \
  'resource.type="batch_task" AND resource.labels.job_uid=~"prod-regular"' \
  --limit=50
```

### Manual Job Trigger (if needed)
```bash
gcloud batch jobs submit prod-regular-screeners-batch-1 \
  --location=us-east5
```

### Check Firestore Results
```bash
python3 backend/jobs/analyze_daily_runs.py 2025-11-20
```

---

## 🔴 Rollback Procedure (Emergency)

### Immediate Rollback (5 minutes)

```bash
# 1. Disable Cloud Batch schedulers
cd terraform/environments/prod
# Comment out module "batch_jobs_pilot" in batch_migration.tf
terraform apply

# 2. Re-enable Cloud Run schedulers
# Uncomment Cloud Scheduler in terraform/modules/scheduled_jobs/main.tf
terraform apply

# 3. Verify Cloud Run resumes
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=1
```

---

## ✅ Validation Criteria (Before Advancing Phase)

| Metric | Target | Command |
|--------|--------|---------|
| Success Rate | 100% (no failures) | `gcloud batch jobs list` |
| Runtime | 95-100 min | Check job logs |
| Firestore Results | Match expected | `analyze_daily_runs.py` |
| Spot Preemptions | <5% | Check logs for "preempted" |
| Cost Per Run | <$0.02 | Billing dashboard |

---

## 💰 Cost Tracking

| System | Cost per Run | Daily (5 batches) | Monthly (20 days) |
|--------|--------------|-------------------|-------------------|
| **Cloud Run** | $0.30 | $1.50 | $30.00 |
| **Cloud Batch** | $0.01 | $0.05 | $1.04 |
| **Savings** | -96.5% | -96.5% | **-$28.96** |

---

## 🛠️ Common Issues & Fixes

### Job Failed
```bash
# Check logs
gcloud logging read 'resource.type="batch_task" AND severity>=ERROR' --limit=20

# Retry manually
gcloud batch jobs submit <job-name> --location=us-east5
```

### Spot VM Preempted
**Solution**: Cloud Batch auto-retries. If persistent, switch to standard VMs in Terraform:
```terraform
provisioning_model = "STANDARD"  # Instead of "SPOT"
```

### Permission Denied
```bash
# Verify service account has required roles
gcloud projects get-iam-policy sylvan-earth-477020-u6 \
  --flatten="bindings[].members" \
  --filter="bindings.members:prod-backend-sa@*"
```

### Missing Firestore Results
```bash
# Verify job completed successfully
gcloud batch jobs describe <job-name> --location=us-east5

# Check if results saved to different document path
# Should be: screeners/{screener}/runs/{date}-batch-{num}
```

---

## 📞 Support Resources

- **Migration Guide**: `docs/CLOUD_BATCH_MIGRATION.md`
- **Troubleshooting**: See full guide Section 10
- **Rollback**: See full guide Section 9
- **Cloud Console**: https://console.cloud.google.com/batch

---

## 🎯 Phase-Specific Commands

### Phase 1: Enable Batch 1
```terraform
# Edit terraform/environments/prod/batch_migration.tf
enable_batches = {
  batch-1 = true
  batch-2 = false
  batch-3 = false
  batch-4 = false
  batch-5 = false
}
```

### Phase 2: Enable Batches 1-3
```terraform
enable_batches = {
  batch-1 = true
  batch-2 = true
  batch-3 = true
  batch-4 = false
  batch-5 = false
}
```

### Phase 3: Enable All Batches
```terraform
enable_batches = {
  batch-1 = true
  batch-2 = true
  batch-3 = true
  batch-4 = true
  batch-5 = true
}
```

---

## ⏱️ Expected Timelines

| Day | Activity | Duration |
|-----|----------|----------|
| **Day 0** | Enable Cloud Batch API, grant permissions | 15 min |
| **Day 1** | Deploy Phase 1 (Batch 1) | 30 min |
| **Day 2-5** | Monitor Phase 1 | 5 min/day |
| **Day 6** | Phase 1 validation, deploy Phase 2 | 30 min |
| **Day 7-10** | Monitor Phase 2 | 5 min/day |
| **Day 11** | Phase 2 validation, deploy Phase 3 | 30 min |
| **Day 12-15** | Monitor Phase 3 | 5 min/day |
| **Day 16** | Phase 3 validation, cleanup Cloud Run | 30 min |

**Total Hands-On Time**: ~4 hours
**Total Calendar Time**: 16-20 business days

---

## 📊 Success Indicators

✅ All batches complete successfully daily
✅ Runtime: 95-100 minutes (consistent with Cloud Run)
✅ Firestore results match expected patterns
✅ Cost: ~$0.05/day (95% less than Cloud Run)
✅ No operational issues or alerts
✅ Spot preemption rate <5%

---

## 🚨 Stop/Rollback Triggers

❌ >10% job failure rate (2+ failures in 5 days)
❌ Data integrity issues (missing or incorrect results)
❌ Spot preemption rate >10%
❌ Runtime consistently >120 minutes
❌ Cost >$0.10 per run

**Action**: Immediately rollback using procedure above

---

## 📝 Notes

- Keep Cloud Run infrastructure for 7 days after Phase 3 as backup
- Document any issues or learnings during migration
- Update team on new operational procedures
- Validate cost savings in billing dashboard monthly
