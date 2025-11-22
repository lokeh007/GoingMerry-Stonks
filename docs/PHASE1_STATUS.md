# Phase 1: Pilot Status

**Start Date**: 2025-11-21
**Duration**: 5 business days
**Scope**: Regular Batch 1 only

---

## Deployment Summary

### ✅ Cloud Batch Job Deployed
- **Job Name**: `prod-batch-regular-screeners-batch-1`
- **Job UID**: `prod-batch-regular-8ac9f2e2-4043-40f80`
- **Docker Image**: `us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest`
- **VM Type**: e2-medium (1 vCPU, 1 GB RAM)
- **Provisioning**: SPOT
- **Rate Limit**: 58 req/min
- **Max Runtime**: 3 hours (10800s)
- **Auto-Retry**: Enabled (maxRetryCount=1)
- **Deployed**: 2025-11-21 19:06:42 UTC

### ✅ Cloud Scheduler Created (Parallel Mode)
- **Scheduler Name**: `prod-regular-screeners-batch-1-cb`
- **Schedule**: `30 16 * * 1-5` (4:30 PM ET, Mon-Fri)
- **Target**: Cloud Batch API
- **State**: ENABLED
- **First Run**: 2025-11-22 16:30 ET (Friday)

### ✅ Cloud Run Scheduler (Existing - Still Active)
- **Scheduler Name**: `prod-trigger-regular-screeners-batch-1`
- **Schedule**: `30 16 * * 1-5` (4:30 PM ET, Mon-Fri)
- **Target**: Cloud Run Job
- **State**: ENABLED
- **Status**: Running in parallel for comparison

---

## Parallel Running Mode

**Both systems will run simultaneously:**

| System | Job Name | Schedule | Firestore Doc | Status |
|--------|----------|----------|---------------|--------|
| Cloud Run | prod-regular-screeners-batch-1 | 4:30 PM ET | `2025-11-22-batch-1` | ✅ Active |
| Cloud Batch | prod-batch-regular-screeners-batch-1 | 4:30 PM ET | `2025-11-22-batch-1-cb` | ✅ Active |

**Note**: Different Firestore document paths prevent conflicts.

---

## Daily Monitoring (Days 1-5)

### Morning Routine (10-11 AM ET)

```bash
# 1. Run automated validation
cd /home/nameci/projects/GoingMerry-Stonks
./scripts/validate-migration.sh

# 2. Run daily monitoring report
./scripts/monitor-daily-batch.sh

# 3. Analyze Firestore results
python3 backend/jobs/analyze_daily_runs.py
```

### Manual Checks

```bash
# Check Cloud Batch status
gcloud batch jobs describe prod-batch-regular-screeners-batch-1 --location=us-east5

# Check Cloud Run status
gcloud run jobs executions list --job=prod-regular-screeners-batch-1 --region=us-east5 --limit=1

# View Cloud Batch logs
gcloud logging read 'labels.job_uid="prod-batch-regular-8ac9f2e2-4043-40f80"' --limit=50

# View Cloud Run logs
gcloud run jobs logs read prod-regular-screeners-batch-1 --region=us-east5 --limit=50
```

### Compare Results

```bash
# Check both Firestore documents
# Cloud Run: screeners/undiscovered/runs/2025-11-22-batch-1
# Cloud Batch: screeners/undiscovered/runs/2025-11-22-batch-1-cb

# Compare stock counts (should be within ±10%)
```

---

## Success Metrics (Track Daily)

| Metric | Target | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 |
|--------|--------|-------|-------|-------|-------|-------|
| **Cloud Batch Success** | ✅ | - | - | - | - | - |
| **Cloud Run Success** | ✅ | - | - | - | - | - |
| **CB Runtime (min)** | < 110 | - | - | - | - | - |
| **CR Runtime (min)** | < 110 | - | - | - | - | - |
| **CB Stock Count** | ±10% CR | - | - | - | - | - |
| **Spot Preemptions** | 0 | - | - | - | - | - |
| **Data Corruption** | 0 | - | - | - | - | - |

### Update This Table Daily

Example:
```
| **Cloud Batch Success** | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **CB Runtime (min)** | < 110 | 97.7 | 98.2 | 105.1 | - | 96.8 |
```

---

## Day 5: Go/No-Go Decision

### GO Criteria (All Must Pass)

- [ ] 5/5 Cloud Batch runs succeeded
- [ ] Average runtime < 110 minutes
- [ ] Result counts within ±10% of Cloud Run
- [ ] Zero data corruption in Firestore
- [ ] Zero Spot preemptions (or successful auto-retry)
- [ ] Zero manual interventions required

### If GO → Proceed to Phase 2

```bash
# 1. Disable Cloud Run scheduler
gcloud scheduler jobs pause prod-trigger-regular-screeners-batch-1 --location=us-east1

# 2. Rename Cloud Batch scheduler (remove "-cb")
gcloud scheduler jobs delete prod-regular-screeners-batch-1-cb --location=us-east1 --quiet
./scripts/create-batch-schedulers.sh 1  # Recreate without "-cb"

# 3. Update Firestore document path (remove "-cb" suffix in code)

# 4. Document lessons learned below
```

### If NO-GO → Extend Pilot

- Document issues found
- Fix root causes
- Extend pilot by 5 more days
- Do NOT proceed to Phase 2

---

## Issues Log

### Issue Template
```
**Date**: YYYY-MM-DD
**Severity**: P1/P2/P3
**Description**: What went wrong
**Impact**: User impact / data impact
**Root Cause**: Why it happened
**Fix**: What was done
**Prevention**: How to prevent
```

### Issues Found

_(Update as issues occur)_

---

## Lessons Learned

_(Update at end of Phase 1)_

**What Went Well**:
-

**What Could Be Better**:
-

**Action Items for Phase 2**:
-

---

## Quick Commands Reference

```bash
# Trigger manual Cloud Batch run
gcloud scheduler jobs run prod-regular-screeners-batch-1-cb --location=us-east1

# Trigger manual Cloud Run execution
gcloud run jobs execute prod-regular-screeners-batch-1 --region=us-east5

# Pause Cloud Batch scheduler (emergency)
gcloud scheduler jobs pause prod-regular-screeners-batch-1-cb --location=us-east1

# Resume Cloud Batch scheduler
gcloud scheduler jobs resume prod-regular-screeners-batch-1-cb --location=us-east1

# Emergency rollback
gcloud scheduler jobs pause prod-regular-screeners-batch-1-cb --location=us-east1
# Cloud Run continues automatically

# View all schedulers
gcloud scheduler jobs list --location=us-east1 | grep batch-1
```

---

## Cost Tracking

| Day | Cloud Run | Cloud Batch | Savings |
|-----|-----------|-------------|---------|
| Day 1 | $0.039 | $0.011 | $0.028 (71.8%) |
| Day 2 | $0.039 | $0.011 | $0.028 (71.8%) |
| Day 3 | $0.039 | $0.011 | $0.028 (71.8%) |
| Day 4 | $0.039 | $0.011 | $0.028 (71.8%) |
| Day 5 | $0.039 | $0.011 | $0.028 (71.8%) |
| **Total** | **$0.195** | **$0.055** | **$0.140 (71.8%)** |

---

## Next Steps After Phase 1

**If GO Decision**:
1. Schedule Phase 2 kickoff (Week 2)
2. Brief team on Phase 1 results
3. Update monitoring dashboards
4. Proceed with batches 2-3 deployment

**Timeline**:
- Day 5 (Fri): Go/No-Go decision
- Weekend: Team reviews results
- Monday Week 2: Phase 2 kickoff (if GO)

---

**Status**: 🟢 ACTIVE
**Last Updated**: 2025-11-21
**Next Review**: 2025-11-22 (Daily)
