# Cloud Batch Migration Plan

**Project**: GoingMerry-Stonks
**Author**: Cloud Migration Team
**Date**: 2025-11-21
**Status**: Ready for Execution

---

## Executive Summary

Migrate daily screener jobs from Cloud Run Jobs to Google Cloud Batch with Spot VMs to achieve **71.8% cost reduction** ($4.20/month savings) while maintaining identical functionality and reliability.

**Pilot Test Results (Batch 1)**:
- ✅ Runtime: 97.7 minutes (within SLA)
- ✅ Tickers processed: 993
- ✅ Results: 58 Undiscovered + 4 Coiled Spring
- ✅ Firestore integration: Working
- ✅ Cost: $0.011 vs $0.039 (Cloud Run)

---

## 1. Current State Analysis

### 1.1 Existing Infrastructure

| Job Name | Type | Schedule | Tickers | Runtime | Cost/run |
|----------|------|----------|---------|---------|----------|
| prod-regular-screeners-batch-1 | Cloud Run | 4:30 PM ET | 992 | ~95m | $0.039 |
| prod-regular-screeners-batch-2 | Cloud Run | 6:00 PM ET | 992 | ~95m | $0.039 |
| prod-regular-screeners-batch-3 | Cloud Run | 7:30 PM ET | 992 | ~95m | $0.039 |
| prod-regular-screeners-batch-4 | Cloud Run | 9:00 PM ET | 992 | ~95m | $0.039 |
| prod-regular-screeners-batch-5 | Cloud Run | 10:30 PM ET | 992 | ~95m | $0.039 |
| prod-smart-money-batch-1 | Cloud Run | 12:00 AM ET | ~1200 | ~120m | $0.049 |
| prod-smart-money-batch-2 | Cloud Run | 2:00 AM ET | ~1200 | ~120m | $0.049 |
| prod-smart-money-batch-3 | Cloud Run | 4:00 AM ET | ~1200 | ~120m | $0.049 |
| prod-smart-money-batch-4 | Cloud Run | 6:00 AM ET | ~1200 | ~120m | $0.049 |
| prod-smart-money-batch-5 | Cloud Run | 8:00 AM ET | ~1200 | ~120m | $0.049 |

**Total**: 10 jobs, ~$0.44/day, ~$13.20/month

### 1.2 Dependencies
- **Docker Image**: `us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest`
- **Service Account**: `prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com`
- **Firestore**: Results stored in `screeners/{screener}/runs/{date}-batch-{n}`
- **Cloud Schedulers**: 10 schedulers triggering jobs
- **Frontend**: Reads from Firestore (no changes needed)

---

## 2. Migration Strategy

### 2.1 Principles
- **Phased Rollout**: Gradual migration with validation gates
- **Parallel Running**: Keep Cloud Run as backup during migration
- **Data Integrity**: Validate Firestore results at each phase
- **Rollback Ready**: Quick rollback procedures documented
- **Zero User Impact**: Frontend continues working seamlessly

### 2.2 Success Criteria
For each phase:
- ✅ All Cloud Batch jobs complete successfully
- ✅ Runtime within SLA (< 110 minutes)
- ✅ Firestore documents created correctly
- ✅ Result counts match historical averages (±10%)
- ✅ No data corruption or missing batches
- ✅ Frontend displays results correctly
- ✅ Zero manual intervention required

### 2.3 Validation Period
- **Pilot (Phase 1)**: 5 business days
- **Expansion (Phase 2)**: 5 business days
- **Full Migration (Phase 3)**: 7 business days
- **Total**: 17 business days (~3.5 weeks)

---

## 3. Phase 1: Pilot (Regular Batch 1 Only)

### 3.1 Objectives
- Validate Cloud Batch in production environment
- Confirm Firestore integration works end-to-end
- Test Spot VM preemption handling (if any)
- Establish baseline metrics

### 3.2 Deployment Steps

#### Step 1: Deploy Cloud Batch Job for Batch 1
```bash
# Already completed - prod-batch-test-screeners-batch1-v2 succeeded
# Need to create production version with proper naming

cd /home/nameci/projects/GoingMerry-Stonks

# Create production deployment script
cp scripts/deploy-cloud-batch-test.sh scripts/deploy-cloud-batch-prod.sh

# Update job naming from "test" to "prod"
# Job name: prod-batch-regular-screeners-batch-1 (Cloud Batch version)
```

#### Step 2: Create Cloud Scheduler for Cloud Batch
```bash
# Create new scheduler with "-cb" suffix (Cloud Batch)
gcloud scheduler jobs create http prod-regular-screeners-batch-1-cb \
  --location=us-east1 \
  --schedule="30 16 * * 1-5" \
  --time-zone="America/New_York" \
  --uri="https://batch.googleapis.com/v1/projects/sylvan-earth-477020-u6/locations/us-east5/jobs" \
  --http-method=POST \
  --message-body='{
    "job": {
      "taskGroups": [...],
      "allocationPolicy": {...}
    }
  }' \
  --headers="Content-Type=application/json" \
  --oauth-service-account-email="prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
```

**Note**: Cloud Scheduler will submit Cloud Batch jobs directly via API.

#### Step 3: Run Parallel for 5 Days
- Keep existing Cloud Run scheduler active
- Enable Cloud Batch scheduler
- Both run daily at 4:30 PM ET
- Results saved to different Firestore docs:
  - Cloud Run: `2025-11-21-batch-1` (existing)
  - Cloud Batch: `2025-11-21-batch-1-cb` (new)

#### Step 4: Daily Validation
```bash
# Check both jobs completed
gcloud run jobs executions list --job=prod-regular-screeners-batch-1 --limit=1
gcloud batch jobs list --filter="labels.batch=1" --limit=1

# Analyze results
python3 backend/jobs/analyze_daily_runs.py

# Compare result counts (should be within 10%)
```

#### Step 5: Metrics Collection (5 Days)
Track:
- Success rate (target: 100%)
- Runtime (target: < 110 minutes)
- Cost per run (target: < $0.015)
- Spot preemptions (acceptable: 0)
- Result count variance (acceptable: ±10%)

### 3.3 Go/No-Go Decision (Day 5)

**GO Criteria**:
- ✅ 5/5 successful runs
- ✅ Average runtime < 110 minutes
- ✅ Result counts within ±10% of Cloud Run
- ✅ Zero data corruption
- ✅ Zero Spot preemptions (or successful retry)

**NO-GO Actions**:
- Document issues found
- Fix root causes
- Extend pilot by 5 more days
- Do NOT proceed to Phase 2

### 3.4 Phase 1 Completion
If GO:
- Disable Cloud Run scheduler for batch-1
- Rename Cloud Batch scheduler (remove "-cb" suffix)
- Update Firestore document path to standard format
- Archive Cloud Run job (do not delete yet)
- Document lessons learned

---

## 4. Phase 2: Expansion (Regular Batches 1-3)

### 4.1 Objectives
- Scale to 60% of regular screeners
- Validate no resource contention
- Confirm Firestore handles concurrent writes
- Test overnight processing

### 4.2 Deployment Steps

#### Step 1: Deploy Cloud Batch for Batches 2-3
```bash
# Deploy batch 2
./scripts/deploy-cloud-batch-prod.sh 2

# Deploy batch 3
./scripts/deploy-cloud-batch-prod.sh 3
```

#### Step 2: Create Cloud Schedulers
```bash
# Batch 2 - 6:00 PM ET
gcloud scheduler jobs create http prod-regular-screeners-batch-2-cb \
  --location=us-east1 \
  --schedule="0 18 * * 1-5" \
  --time-zone="America/New_York" \
  [...]

# Batch 3 - 7:30 PM ET
gcloud scheduler jobs create http prod-regular-screeners-batch-3-cb \
  --location=us-east1 \
  --schedule="30 19 * * 1-5" \
  --time-zone="America/New_York" \
  [...]
```

#### Step 3: Run Parallel for 5 Days
- Cloud Run: batches 1-3
- Cloud Batch: batches 1-3 (with "-cb" suffix)
- Compare daily results

#### Step 4: Daily Validation
```bash
# Check all batch jobs
for i in 1 2 3; do
  echo "=== Batch $i ==="
  gcloud run jobs executions list --job=prod-regular-screeners-batch-$i --limit=1
  gcloud batch jobs list --filter="labels.batch=$i" --limit=1
done

# Analyze aggregated results
python3 backend/jobs/analyze_daily_runs.py
```

#### Step 5: Metrics Collection (5 Days)
Same as Phase 1, but for 3 batches.

### 4.3 Go/No-Go Decision (Day 5)

**GO Criteria**:
- ✅ 15/15 successful runs (5 days × 3 batches)
- ✅ No Firestore write conflicts
- ✅ No resource contention
- ✅ Frontend performance unchanged

**NO-GO Actions**:
- Roll back to Phase 1 (batch 1 only on Cloud Batch)
- Keep batches 2-3 on Cloud Run
- Fix issues, retry Phase 2

### 4.4 Phase 2 Completion
If GO:
- Disable Cloud Run schedulers for batches 1-3
- Rename Cloud Batch schedulers (remove "-cb")
- Update monitoring dashboards
- Document lessons learned

---

## 5. Phase 3: Full Migration (Regular Batches 1-5 + Smart Money 1-5)

### 5.1 Objectives
- Migrate all 10 jobs to Cloud Batch
- Achieve full 71.8% cost savings
- Validate overnight Smart Money processing
- Ensure zero operational issues

### 5.2 Deployment Steps

#### Step 1: Deploy Remaining Regular Batches
```bash
# Deploy batches 4-5
./scripts/deploy-cloud-batch-prod.sh 4
./scripts/deploy-cloud-batch-prod.sh 5
```

#### Step 2: Deploy Smart Money Batches
```bash
# Create Smart Money deployment script
cp scripts/deploy-cloud-batch-prod.sh scripts/deploy-cloud-batch-smart-money.sh

# Modify for Smart Money screeners
# - Change docker image or ensure it supports both screener types
# - Adjust environment variables (SCREENER_TYPE=smart_money)

# Deploy all 5 Smart Money batches
for i in 1 2 3 4 5; do
  ./scripts/deploy-cloud-batch-smart-money.sh $i
done
```

#### Step 3: Create All Cloud Schedulers
```bash
# Regular batches 4-5
gcloud scheduler jobs create http prod-regular-screeners-batch-4-cb [...]
gcloud scheduler jobs create http prod-regular-screeners-batch-5-cb [...]

# Smart Money batches 1-5
gcloud scheduler jobs create http prod-smart-money-batch-1-cb [...]
gcloud scheduler jobs create http prod-smart-money-batch-2-cb [...]
gcloud scheduler jobs create http prod-smart-money-batch-3-cb [...]
gcloud scheduler jobs create http prod-smart-money-batch-4-cb [...]
gcloud scheduler jobs create http prod-smart-money-batch-5-cb [...]
```

#### Step 4: Run Parallel for 7 Days
- All 10 Cloud Run jobs active
- All 10 Cloud Batch jobs active (with "-cb" suffix)
- Compare daily results across all batches

#### Step 5: Daily Validation
```bash
# Comprehensive check script
./scripts/validate-migration.sh

# Contents:
# - Check all 10 Cloud Batch jobs succeeded
# - Check all 10 Cloud Run jobs succeeded (for comparison)
# - Analyze Firestore results
# - Compare result counts
# - Generate daily report
```

#### Step 6: Metrics Collection (7 Days)
Track:
- Success rate across all 10 jobs (target: 100%)
- Total daily runtime (target: < 12 hours)
- Daily cost (target: < $0.125)
- Overnight processing reliability
- Zero manual interventions

### 5.3 Go/No-Go Decision (Day 7)

**GO Criteria**:
- ✅ 70/70 successful runs (7 days × 10 batches)
- ✅ Average daily cost < $0.125
- ✅ No operational issues
- ✅ Frontend performance unchanged
- ✅ User reports: zero issues

**NO-GO Actions**:
- Keep Cloud Run as primary
- Keep Cloud Batch as secondary
- Extend validation by 7 more days
- Fix any issues found

### 5.4 Phase 3 Completion
If GO:
- Disable all Cloud Run schedulers
- Rename all Cloud Batch schedulers (remove "-cb")
- Update all monitoring dashboards
- Update CLAUDE.md documentation
- Proceed to Phase 4 (decommission)

---

## 6. Phase 4: Decommission Cloud Run Jobs

### 6.1 Objectives
- Safely remove Cloud Run infrastructure
- Archive historical data
- Update documentation
- Realize full cost savings

### 6.2 Grace Period
**Wait 14 days** after Phase 3 completion before decommissioning.

**Why?**
- Ensure no hidden issues emerge
- Allow time for rollback if needed
- Build confidence in Cloud Batch stability

### 6.3 Decommission Steps

#### Step 1: Archive Cloud Run Configurations
```bash
# Export all Cloud Run job definitions
for i in 1 2 3 4 5; do
  gcloud run jobs describe prod-regular-screeners-batch-$i --region=us-east5 \
    --format=yaml > archive/cloud-run/regular-batch-$i.yaml

  gcloud run jobs describe prod-smart-money-batch-$i --region=us-east5 \
    --format=yaml > archive/cloud-run/smart-money-batch-$i.yaml
done

# Commit to git
git add archive/cloud-run/
git commit -m "Archive Cloud Run job definitions before decommission"
```

#### Step 2: Delete Cloud Schedulers
```bash
# Delete old Cloud Run schedulers
for i in 1 2 3 4 5; do
  gcloud scheduler jobs delete prod-regular-screeners-batch-$i --location=us-east1 --quiet
  gcloud scheduler jobs delete prod-smart-money-batch-$i --location=us-east1 --quiet
done

# Verify only Cloud Batch schedulers remain
gcloud scheduler jobs list --location=us-east1
```

#### Step 3: Delete Cloud Run Jobs
```bash
# Delete regular screener jobs
for i in 1 2 3 4 5; do
  gcloud run jobs delete prod-regular-screeners-batch-$i --region=us-east5 --quiet
done

# Delete Smart Money screener jobs
for i in 1 2 3 4 5; do
  gcloud run jobs delete prod-smart-money-batch-$i --region=us-east5 --quiet
done

# Verify deletion
gcloud run jobs list --region=us-east5
```

#### Step 4: Update Documentation
```bash
# Update CLAUDE.md
# - Remove Cloud Run Jobs from architecture diagram
# - Update deployment instructions
# - Update monitoring dashboards

# Update README.md
# - Remove Cloud Run references
# - Add Cloud Batch documentation

# Update deployment scripts
# - Archive old Cloud Run deployment scripts
# - Make Cloud Batch scripts the default
```

#### Step 5: Update Terraform (Optional)
If we decide to manage Cloud Batch with Terraform in the future:
```bash
cd terraform/environments/prod

# Remove Cloud Run job resources
# Add Cloud Batch resources (when provider supports it)

terraform plan
terraform apply
```

#### Step 6: Clean Up Monitoring
```bash
# Remove Cloud Run-specific alerts
gcloud alpha monitoring policies list --filter="displayName:Cloud Run"

# Update dashboards to show only Cloud Batch metrics
# Remove Cloud Run panels from monitoring dashboards
```

### 6.4 Phase 4 Completion Checklist
- ✅ All Cloud Run jobs deleted
- ✅ All old schedulers deleted
- ✅ Configurations archived in git
- ✅ Documentation updated
- ✅ Monitoring dashboards updated
- ✅ Team notified of migration completion
- ✅ Post-mortem document created

---

## 7. Rollback Procedures

### 7.1 Emergency Rollback (< 1 hour)

If Cloud Batch fails during any phase:

```bash
# 1. Disable Cloud Batch schedulers immediately
gcloud scheduler jobs pause prod-regular-screeners-batch-1-cb --location=us-east1
gcloud scheduler jobs pause prod-regular-screeners-batch-2-cb --location=us-east1
# ... (disable all affected batches)

# 2. Re-enable Cloud Run schedulers
gcloud scheduler jobs resume prod-regular-screeners-batch-1 --location=us-east1
gcloud scheduler jobs resume prod-regular-screeners-batch-2 --location=us-east1
# ... (resume all affected batches)

# 3. Trigger manual Cloud Run execution if schedule missed
gcloud run jobs execute prod-regular-screeners-batch-1 --region=us-east5

# 4. Notify team and create incident report
```

### 7.2 Rollback Decision Tree

**Trigger Rollback If**:
- ❌ Cloud Batch success rate < 80% over 3 days
- ❌ Data corruption detected in Firestore
- ❌ Spot VM preemptions cause > 2 failures/week
- ❌ Runtime exceeds 120 minutes consistently
- ❌ Frontend issues reported by users

**Do NOT Rollback For**:
- ✅ Single job failure (retry handles it)
- ✅ Minor runtime variance (± 15 minutes)
- ✅ Cost slightly higher than expected (< 10%)

---

## 8. Monitoring & Alerting

### 8.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Success Rate | 100% | < 95% over 3 days |
| Runtime (Regular) | < 100m | > 110m for 2 consecutive runs |
| Runtime (Smart Money) | < 120m | > 135m for 2 consecutive runs |
| Cost per Run (Regular) | $0.011 | > $0.020 |
| Cost per Run (Smart Money) | $0.014 | > $0.025 |
| Spot Preemptions | 0 | > 1 per week |
| Firestore Write Errors | 0 | > 0 |

### 8.2 Daily Monitoring Script

Create `scripts/monitor-daily-batch.sh`:

```bash
#!/bin/bash
# Daily Cloud Batch monitoring report

DATE=$(TZ=America/New_York date +%Y-%m-%d)
echo "==============================================="
echo "Daily Batch Report - $DATE"
echo "==============================================="

# Check all batch jobs
for i in 1 2 3 4 5; do
  echo "Regular Batch $i:"
  gcloud batch jobs list --filter="labels.batch=$i AND createTime>$DATE" \
    --format="table(name,state,runDuration)" | tail -1

  echo "Smart Money Batch $i:"
  gcloud batch jobs list --filter="labels.batch=$i AND labels.type=smart-money AND createTime>$DATE" \
    --format="table(name,state,runDuration)" | tail -1
done

# Analyze Firestore results
echo ""
echo "Firestore Results:"
python3 backend/jobs/analyze_daily_runs.py

# Cost summary
echo ""
echo "Cost Estimate:"
echo "10 batches × $0.0125/run = $0.125/day"
```

Run via cron:
```bash
# Add to crontab (runs at 11 AM ET daily)
0 11 * * * cd /home/nameci/projects/GoingMerry-Stonks && ./scripts/monitor-daily-batch.sh | mail -s "Daily Batch Report" your-email@example.com
```

### 8.3 Cloud Monitoring Alerts

Create alerts in GCP:

```bash
# Alert: Cloud Batch Job Failed
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Batch Job Failed" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s \
  --condition-display-name="Batch job failed" \
  --condition-threshold-filter='resource.type="batch.googleapis.com/Job" AND metric.type="batch.googleapis.com/job/failed_count"'

# Alert: Cloud Batch High Runtime
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Batch Runtime > 110 minutes" \
  --condition-threshold-value=6600 \
  --condition-threshold-duration=60s \
  --condition-display-name="Runtime exceeded" \
  --condition-threshold-filter='resource.type="batch.googleapis.com/Job" AND metric.type="batch.googleapis.com/job/run_duration"'
```

---

## 9. Cost Analysis

### 9.1 Current State (Cloud Run Jobs)

| Component | Quantity | Cost | Daily | Monthly |
|-----------|----------|------|-------|---------|
| Regular Screeners | 5 jobs | $0.039/run | $0.195 | $5.85 |
| Smart Money | 5 jobs | $0.049/run | $0.245 | $7.35 |
| **Total** | **10 jobs** | - | **$0.44** | **$13.20** |

### 9.2 Future State (Cloud Batch + Spot VMs)

| Component | Quantity | Cost | Daily | Monthly |
|-----------|----------|------|-------|---------|
| Regular Screeners | 5 jobs | $0.011/run | $0.055 | $1.65 |
| Smart Money | 5 jobs | $0.014/run | $0.070 | $2.10 |
| **Total** | **10 jobs** | - | **$0.125** | **$3.75** |

### 9.3 Savings Summary

| Metric | Value |
|--------|-------|
| **Absolute Savings** | **$9.45/month** |
| **Percentage Savings** | **71.6%** |
| **Annual Savings** | **$113.40/year** |
| **ROI** | Immediate (no migration cost) |

### 9.4 Break-Even Analysis
- Migration effort: ~16 hours (planning + execution + validation)
- Savings: $9.45/month
- Break-even: 1.7 months
- **Net benefit after 1 year**: $113.40 savings

---

## 10. Risk Assessment

### 10.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Spot VM preemption | Low | Medium | Auto-retry (maxRetryCount=1) |
| Firestore write conflicts | Very Low | High | Batch-specific doc IDs prevent conflicts |
| Network connectivity | Very Low | Medium | External IP enabled |
| Image pull failures | Very Low | High | Service account has artifactregistry.reader |
| Data corruption | Very Low | Critical | Parallel running during migration validates results |
| Scheduler failures | Very Low | Medium | Cloud Scheduler has 99.9% SLA |
| Cost overruns | Very Low | Low | Spot VMs have fixed pricing |

### 10.2 Risk Mitigation Strategies

1. **Spot Preemption**:
   - Configure `maxRetryCount=1` for automatic retry
   - Use `provisioningModel: SPOT` with fallback to standard
   - Monitor preemption rate (should be < 5% for e2-medium)

2. **Data Integrity**:
   - Run parallel Cloud Run + Cloud Batch during migration
   - Compare results daily
   - Validate Firestore documents have expected structure

3. **Operational Risk**:
   - Document rollback procedures
   - Train team on Cloud Batch monitoring
   - Keep Cloud Run jobs for 14 days post-migration

---

## 11. Timeline

### 11.1 Gantt Chart

```
Week 1  Week 2  Week 3  Week 4  Week 5  Week 6
|-------|-------|-------|-------|-------|-------|
[Phase 1: Pilot - Batch 1        ]
        [Phase 2: Batches 1-3           ]
                [Phase 3: All 10 batches          ]
                                [Grace Period     ]
                                        [Phase 4  ]
```

### 11.2 Detailed Schedule

| Phase | Duration | Start | End | Deliverable |
|-------|----------|-------|-----|-------------|
| **Phase 1** | 5 days | Mon Week 1 | Fri Week 1 | Batch 1 validated |
| Go/No-Go | 1 day | Mon Week 2 | Mon Week 2 | Decision documented |
| **Phase 2** | 5 days | Tue Week 2 | Mon Week 3 | Batches 1-3 validated |
| Go/No-Go | 1 day | Tue Week 3 | Tue Week 3 | Decision documented |
| **Phase 3** | 7 days | Wed Week 3 | Tue Week 4 | All 10 batches validated |
| Go/No-Go | 1 day | Wed Week 4 | Wed Week 4 | Decision documented |
| **Grace Period** | 14 days | Thu Week 4 | Wed Week 6 | Stability confirmed |
| **Phase 4** | 3 days | Thu Week 6 | Mon Week 7 | Cloud Run decommissioned |

**Total Duration**: 37 business days (~7.5 weeks)

### 11.3 Key Milestones

- ✅ **M1**: Pilot successful (Day 5)
- ✅ **M2**: 60% migrated (Day 11)
- ✅ **M3**: 100% migrated (Day 18)
- ✅ **M4**: Cloud Run decommissioned (Day 37)

---

## 12. Documentation Updates

### 12.1 Files to Update

| File | Changes Required |
|------|------------------|
| `CLAUDE.md` | Update architecture diagram, remove Cloud Run Jobs |
| `README.md` | Update deployment instructions |
| `DEPLOYMENT_STATUS.md` | Change Cloud Run Jobs → Cloud Batch |
| `docs/CLOUD_BATCH_MANUAL_DEPLOY.md` | Production best practices |
| `terraform/environments/prod/batch_migration.tf` | Document manual deployment approach |

### 12.2 New Documentation

Create:
- ✅ `docs/CLOUD_BATCH_MIGRATION_PLAN.md` (this document)
- `docs/CLOUD_BATCH_OPERATIONS.md` (day-to-day operations guide)
- `docs/CLOUD_BATCH_TROUBLESHOOTING.md` (common issues + fixes)

---

## 13. Success Criteria Summary

Migration is successful when:

✅ **Functionality**
- All 10 batches run daily without manual intervention
- Results saved correctly to Firestore
- Frontend displays results with < 1 second load time
- Zero data loss or corruption

✅ **Performance**
- Regular screeners: < 110 minutes/run
- Smart Money screeners: < 135 minutes/run
- Success rate: ≥ 99% over 30 days

✅ **Cost**
- Daily cost: < $0.15
- Monthly cost: < $4.50
- Savings: ≥ 65% vs Cloud Run

✅ **Reliability**
- Zero manual interventions required
- Auto-retry handles transient failures
- Spot preemptions: < 1/week

✅ **Operations**
- Team trained on Cloud Batch monitoring
- Documentation complete and accurate
- Rollback procedures tested

---

## 14. Post-Migration Review

### 14.1 30-Day Retrospective

After 30 days in production, conduct review:

**Questions**:
1. Did we achieve 71.6% cost savings?
2. What issues emerged that weren't anticipated?
3. How many manual interventions were required?
4. What would we do differently next time?
5. Should we optimize further (e.g., smaller VMs)?

**Document**:
- Actual vs expected cost
- Actual vs expected reliability
- Lessons learned
- Recommendations for future migrations

### 14.2 Continuous Improvement

**Optimization Opportunities**:
- Reduce VM size to e2-small (512 MB) if memory allows → +30% savings
- Implement batch parallelization (process 2 batches simultaneously) → 50% faster
- Migrate to preemptible TPUs for even lower cost (experimental)
- Implement result caching to reduce API calls

---

## 15. Appendix

### A. Required IAM Permissions

Service account `prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com` needs:

```bash
# Already granted:
- roles/batch.agentReporter
- roles/artifactregistry.reader
- roles/datastore.user (Firestore)
- roles/secretmanager.secretAccessor

# May need (verify):
- roles/logging.logWriter
- roles/monitoring.metricWriter
```

### B. Docker Image Requirements

Ensure `daily-screeners:latest` includes:
- Python 3.11+
- All dependencies from `requirements.txt`
- Environment variable support for `BATCH_NUMBER`, `SCREENER_TYPE`
- Proper exit codes (0 = success, non-zero = failure)

### C. Cloud Scheduler Payload Example

```json
{
  "job": {
    "name": "prod-batch-regular-screeners-batch-1",
    "taskGroups": [{
      "taskSpec": {
        "runnables": [{
          "container": {
            "imageUri": "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest",
            "commands": ["python", "/app/jobs/run_daily_screeners.py"]
          },
          "environment": {
            "variables": {
              "BATCH_NUMBER": "1",
              "GCP_PROJECT_ID": "sylvan-earth-477020-u6",
              "ENVIRONMENT": "prod",
              "PYTHONUNBUFFERED": "1",
              "RATE_LIMIT_PER_MINUTE": "58",
              "SCREENER_TYPE": "regular"
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
        "email": "prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com"
      }
    },
    "logsPolicy": {
      "destination": "CLOUD_LOGGING"
    },
    "labels": {
      "environment": "prod",
      "batch": "1",
      "type": "regular-screeners"
    }
  }
}
```

### D. Contact Information

**Migration Team**:
- Lead: [Your Name]
- GCP Admin: [Admin Name]
- On-Call: [Rotation Schedule]

**Escalation**:
- Severity 1 (Production down): Page on-call immediately
- Severity 2 (Degraded): Create incident, notify team
- Severity 3 (Minor issue): Create ticket, fix during business hours

---

## 16. Approval Sign-Off

This migration plan requires approval from:

- [ ] **Engineering Lead**: _____________________ Date: _______
- [ ] **DevOps/SRE**: _____________________ Date: _______
- [ ] **Finance** (for cost validation): _____________________ Date: _______
- [ ] **Product** (for user impact): _____________________ Date: _______

**Approved to proceed**: Yes / No
**Notes**: _______________________________________________________________

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Next Review**: After Phase 1 completion (Week 1)
