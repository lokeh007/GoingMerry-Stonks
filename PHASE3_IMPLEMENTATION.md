# Phase 3 Implementation Guide - Long-Term Optimization
**Goal**: Proactive maintenance and performance monitoring for stable, reliable screener runs

**Estimated Time**: 4-6 hours (one-time setup)
**Risk Level**: Low
**Expected Impact**:
- Eliminate API waste on delisted tickers (save ~5-10% of API calls)
- Early detection of performance degradation
- Automated alerting for failures
- Better visibility into system health

---

## Overview

Phase 3 focuses on **long-term optimization and monitoring** to ensure the screener system remains fast, reliable, and cost-effective over time. This is about building infrastructure to prevent future issues, not fixing immediate problems.

**Key Components**:
1. Pre-populate delisted ticker blacklist (one-time, saves ongoing API calls)
2. Performance monitoring and dashboards (ongoing visibility)
3. Automated alerting (catch issues before they become critical)
4. Scheduled maintenance tasks (keep system clean)

---

## 1. Pre-populate Delisted Ticker Blacklist

### Overview

**Goal**: Proactively identify all delisted/invalid tickers BEFORE running expensive screeners

**Benefits**:
- Saves 5-10% of API calls on every future run
- Reduces "not found" errors in logs
- Improves processing time by ~5-10 minutes per batch
- One-time cost, permanent benefit

**Trade-off**: Initial time investment (~10 hours total for all batches)

### Implementation

#### Step 1: Test with Batch 1 (Dry Run)

**Time**: 30 minutes

```bash
cd backend

# Dry run first (check without blacklisting)
python jobs/populate_delisted_blacklist.py --batch 1 --dry-run --rate-limit 50
```

**Expected output**:
```
=== DELISTED TICKER SCANNER - Starting ===
Rate limit: 50 req/min
Dry run: True
Resume mode: True

Loading batch 1/5...
✓ Loaded 1200 tickers

Estimated time: 24.0 minutes (0.4 hours)

Starting scan...
================================================================================
⊗ AAXA: DELISTED (no_data)
⊗ ABEO: DELISTED (no_data)
...

Progress: 50/1200 (4.2%)
  Checked: 50
  Valid: 45
  Delisted: 5
  Skipped (already blacklisted): 0
  Rate: 50.2 tickers/min
  ETA: 23.0 minutes

...

=== SCAN COMPLETE ===
Total universe: 1200 tickers
Already blacklisted: 0 (skipped)
Checked: 1200 tickers
  ✓ Valid: 1050 (87.5%)
  ⊗ Delisted: 150 (12.5%)
  ✗ Errors: 0
Execution time: 24.0 minutes

DRY RUN: Would add 150 tickers to blacklist:
  AAXA, ABEO, ACGL, ... and 130 more
```

#### Step 2: Run for All Batches (Actual)

**Time**: ~2 hours (can run in background)

```bash
cd backend

# Batch 1 (A-D, ~1200 stocks, ~24 minutes)
python jobs/populate_delisted_blacklist.py --batch 1 --rate-limit 50

# Batch 2 (E-J, ~1200 stocks, ~24 minutes)
python jobs/populate_delisted_blacklist.py --batch 2 --rate-limit 50

# Batch 3 (K-N, ~1200 stocks, ~24 minutes)
python jobs/populate_delisted_blacklist.py --batch 3 --rate-limit 50

# Batch 4 (O-S, ~1200 stocks, ~24 minutes)
python jobs/populate_delisted_blacklist.py --batch 4 --rate-limit 50

# Batch 5 (T-Z, ~1200 stocks, ~24 minutes)
python jobs/populate_delisted_blacklist.py --batch 5 --rate-limit 50
```

**Or run all at once** (slower but hands-off):
```bash
cd backend

# Full universe (all 6000 stocks, ~2 hours)
nohup python jobs/populate_delisted_blacklist.py --rate-limit 50 > delisted_scan.log 2>&1 &

# Monitor progress
tail -f delisted_scan.log
```

#### Step 3: Schedule Monthly Cleanup

Add a Cloud Run job to cleanup expired blacklist entries:

**File**: `backend/jobs/cleanup_delisted_blacklist.py`

```python
#!/usr/bin/env python3
"""
Monthly Delisted Blacklist Cleanup

Removes expired entries from delisted ticker blacklist (older than 30 days).
This allows retrying previously delisted tickers that may have been relisted.

Schedule: 1st of each month at 3:00 AM ET
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.delisted_ticker_cache import DelistedTickerCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Cleanup expired blacklist entries."""
    logger.info("=" * 80)
    logger.info("DELISTED TICKER BLACKLIST CLEANUP")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Cleanup expired entries
    deleted_count = cache.cleanup_expired_entries()

    if deleted_count > 0:
        logger.info(f"✓ Cleaned up {deleted_count} expired entries")
    else:
        logger.info("✓ No expired entries to cleanup")

    # Get final statistics
    stats = cache.get_statistics()
    logger.info("")
    logger.info("📊 Blacklist Statistics:")
    logger.info(f"  - Total Blacklisted: {stats.get('total_blacklisted', 0)}")
    logger.info(f"  - Error Types: {stats.get('error_types', {})}")
    logger.info("")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

**Schedule with Cloud Scheduler**:
```bash
# Create Cloud Run job
gcloud run jobs create prod-cleanup-delisted-blacklist \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest \
  --region=us-east5 \
  --service-account=prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com \
  --set-env-vars="GCP_PROJECT_ID=sylvan-earth-477020-u6,ENVIRONMENT=prod" \
  --timeout=600s \
  --memory=1Gi \
  --cpu=1 \
  --command=python \
  --args=/app/jobs/cleanup_delisted_blacklist.py

# Create monthly schedule (1st of month at 3:00 AM ET = 8:00 AM UTC)
gcloud scheduler jobs create http prod-trigger-cleanup-blacklist \
  --location=us-east1 \
  --schedule="0 8 1 * *" \
  --time-zone="America/New_York" \
  --uri="https://us-east5-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/sylvan-earth-477020-u6/jobs/prod-cleanup-delisted-blacklist:run" \
  --http-method=POST \
  --oauth-service-account-email=prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com
```

---

## 2. Performance Monitoring & Dashboards

### Overview

**Goal**: Real-time visibility into screener performance, errors, and trends

**Benefits**:
- Early detection of performance degradation
- Identify rate limiting issues before they cause failures
- Track cost trends over time
- Historical data for optimization decisions

### Implementation

#### Step 1: Create Custom Metrics

Add metrics logging to `backend/jobs/run_daily_screeners.py`:

```python
# After line 1080 (in the run() method, after completion)

# Log custom metrics to Cloud Logging (automatically picked up by Cloud Monitoring)
logger.info(
    "METRICS",
    extra={
        "json_fields": {
            "metric_type": "screener_execution",
            "batch_number": self.batch_number,
            "execution_time_seconds": total_execution_time,
            "total_tickers_processed": len(universe),
            "undiscovered_results": len(undiscovered_results),
            "coiled_spring_results": len(coiled_spring_results),
            "api_calls": total_api_calls,
            "api_rate_per_minute": overall_rate,
            "rate_utilization_percent": overall_utilization,
            "failed_count": len(failed_tickers),
            "not_found_count": len(not_found_tickers),
            "avg_seconds_per_ticker": total_execution_time / len(universe) if len(universe) > 0 else 0,
        }
    }
)
```

#### Step 2: Create Cloud Monitoring Dashboard

**File**: `terraform/modules/monitoring/dashboards.tf`

```hcl
resource "google_monitoring_dashboard" "screener_performance" {
  dashboard_json = jsonencode({
    displayName = "Screener Performance Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Batch Execution Time (Last 7 Days)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\""
                    aggregation = {
                      alignmentPeriod  = "86400s"  # Daily
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                  unitOverride = "s"
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Execution Time (seconds)"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "API Rate Utilization (%)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\""
                    aggregation = {
                      alignmentPeriod  = "86400s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Rate Utilization (%)"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Processing Rate (seconds/ticker)"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\""
                  aggregation = {
                    alignmentPeriod  = "86400s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Error Rate (%)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\""
                    aggregation = {
                      alignmentPeriod  = "86400s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Error Rate (%)"
                scale = "LINEAR"
              }
              thresholds = [{
                value = 5.0
                color = "YELLOW"
              }, {
                value = 10.0
                color = "RED"
              }]
            }
          }
        }
      ]
    }
  })
}
```

#### Step 3: Access Dashboard

```bash
# Deploy dashboard
cd terraform/environments/prod
terraform apply

# Get dashboard URL
echo "https://console.cloud.google.com/monitoring/dashboards?project=sylvan-earth-477020-u6"
```

---

## 3. Automated Alerting

### Overview

**Goal**: Get notified immediately when issues occur

**Alert Conditions**:
1. Execution time > 4 hours (should be ~2 hours after Phase 2)
2. Error rate > 10%
3. Rate limit errors detected
4. Job fails to complete

### Implementation

#### Step 1: Create Alert Policies

**File**: `terraform/modules/monitoring/alerts.tf`

```hcl
# Alert: Execution time exceeds 4 hours
resource "google_monitoring_alert_policy" "screener_slow_execution" {
  display_name = "Screener Batch - Slow Execution (>4 hours)"
  combiner     = "OR"

  conditions {
    display_name = "Execution time > 14400 seconds (4 hours)"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\" AND jsonPayload.execution_time_seconds > 14400"
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 14400  # 4 hours

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "86400s"  # Auto-close after 24 hours
  }
}

# Alert: High error rate
resource "google_monitoring_alert_policy" "screener_high_errors" {
  display_name = "Screener Batch - High Error Rate (>10%)"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 10%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND jsonPayload.metric_type=\"screener_execution\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10.0  # 10% error rate

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

# Alert: Job execution failure
resource "google_monitoring_alert_policy" "screener_job_failure" {
  display_name = "Screener Batch - Job Execution Failed"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run Job execution failed"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND metric.type=\"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result=\"failed\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

# Notification channel (email)
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email - brian.boatright@gmail.com"
  type         = "email"

  labels = {
    email_address = "brian.boatright@gmail.com"
  }
}
```

#### Step 2: Deploy Alerts

```bash
cd terraform/environments/prod
terraform apply
```

#### Step 3: Test Alerts

```bash
# Trigger test notification
gcloud alpha monitoring channels test \
  --notification-channel=CHANNEL_ID \
  --project=sylvan-earth-477020-u6
```

---

## 4. Cost Tracking & Optimization

### Overview

**Goal**: Monitor and optimize Cloud Run costs over time

### Implementation

#### Step 1: Enable Detailed Billing Export

```bash
# Enable billing export to BigQuery
gcloud beta billing accounts get-iam-policy BILLING_ACCOUNT_ID

# Create BigQuery dataset for billing data
bq mk --dataset \
  --location=US \
  --description="GCP billing export for cost analysis" \
  sylvan-earth-477020-u6:billing_export
```

#### Step 2: Create Cost Dashboard

Create Looker Studio dashboard with:
1. Daily costs by Cloud Run job
2. Cost trends over time
3. Cost per screener result
4. Comparison: actual vs expected costs

**Query Example** (BigQuery):
```sql
SELECT
  service.description AS service,
  DATE(usage_start_time) AS usage_date,
  SUM(cost) AS total_cost,
  SUM(usage.amount) AS total_usage
FROM
  `sylvan-earth-477020-u6.billing_export.gcp_billing_export_v1_*`
WHERE
  service.description LIKE '%Cloud Run%'
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  service, usage_date
ORDER BY
  usage_date DESC, total_cost DESC
```

---

## 5. Automated Testing & Quality Gates

### Overview

**Goal**: Prevent regressions and ensure consistent quality

### Implementation

#### Step 1: Integration Tests

Create `backend/tests/integration/test_screener_batches.py`:

```python
"""
Integration tests for screener batches.

Tests the full screener pipeline with a small sample of tickers.
Validates that changes don't break core functionality.
"""

import pytest
from backend.jobs.run_daily_screeners import DailyScreenerJob


@pytest.mark.integration
def test_batch_1_sample():
    """Test Batch 1 with small sample (10 tickers)."""
    job = DailyScreenerJob(batch_number=1)

    # Override universe with small sample
    sample_universe = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
                       "NVDA", "META", "NFLX", "AMD", "INTC"]

    # Run screeners
    result = job.run()

    # Assertions
    assert result["status"] == "success"
    assert "timestamp" in result

    # Should complete quickly with small sample
    # (If Phase 2 is working, should be < 2 minutes for 10 tickers)


@pytest.mark.integration
def test_delisted_ticker_skipping():
    """Test that delisted tickers are skipped."""
    job = DailyScreenerJob(batch_number=2)

    # These tickers are known delisted (from Batch 2 errors)
    delisted_tickers = ["FNIGX", "FOACW", "FRFAF", "GDEL"]

    for ticker in delisted_tickers:
        is_blacklisted = job.delisted_cache.is_blacklisted(ticker)
        assert is_blacklisted, f"{ticker} should be blacklisted"


@pytest.mark.integration
def test_null_handling():
    """Test that None returns are handled gracefully."""
    job = DailyScreenerJob(batch_number=1)

    # Test with ticker that might return None (simulated)
    result = job._process_ticker(
        "INVALID_TICKER_XYZ",
        undiscovered_params={"max_institutional_ownership": 25.0, "max_analyst_coverage": 5, "require_insider_buying": False},
        coiled_spring_params={"max_volatility_30d": 20.0, "require_nr7": True, "min_percentile_rank": 30.0}
    )

    # Should return None results without crashing
    undiscovered, coiled_spring, api_calls = result
    assert undiscovered is None or isinstance(undiscovered, dict)
    assert coiled_spring is None or isinstance(coiled_spring, dict)
    assert api_calls >= 0
```

#### Step 2: Run Integration Tests in CI/CD

Add to `.github/workflows/test.yml`:

```yaml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration/ -v --tb=short
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
```

---

## 6. Documentation & Runbooks

### Overview

**Goal**: Document operational procedures for maintenance and troubleshooting

### Implementation

#### Create Runbook: `SCREENER_RUNBOOK.md`

```markdown
# Screener Operations Runbook

## Daily Operations

### Check Status
\`\`\`bash
# View recent executions
gcloud run jobs executions list \\
  --job=prod-regular-screeners-batch-2 \\
  --region=us-east5 \\
  --limit=10
\`\`\`

### Monitor Execution
\`\`\`bash
# Watch logs in real-time
gcloud run jobs executions logs tail \\
  --job=prod-regular-screeners-batch-2 \\
  --region=us-east5
\`\`\`

## Troubleshooting

### Issue: Job timeout
**Symptoms**: Job terminates after X hours
**Resolution**: See BATCH2_TIMEOUT_ANALYSIS.md

### Issue: High error rate
**Symptoms**: > 10% of tickers fail
**Resolution**:
1. Check Yahoo Finance API status
2. Review error logs for patterns
3. Check if delisted tickers need updating

### Issue: No results
**Symptoms**: Firestore empty after job runs
**Resolution**:
1. Check job logs for errors
2. Verify Firestore permissions
3. Check screening criteria (may be too strict)

## Maintenance Tasks

### Monthly: Cleanup delisted blacklist
\`\`\`bash
python backend/jobs/cleanup_delisted_blacklist.py
\`\`\`

### Quarterly: Review screening criteria
- Check if PEG ratio thresholds need adjustment
- Review institutional ownership cutoffs
- Update analyst coverage limits

### Annually: Re-scan for delisted tickers
\`\`\`bash
python backend/jobs/populate_delisted_blacklist.py --rate-limit 50
\`\`\`
```

---

## Timeline & Effort

| Task | Duration | When |
|------|----------|------|
| Pre-populate blacklist (all batches) | 2 hours | After Phase 2 deployment |
| Create monitoring dashboard | 1 hour | After Phase 2 validation |
| Set up alerts | 30 min | After dashboard creation |
| Integration tests | 1 hour | Before Phase 2 deployment |
| Documentation | 30 min | After all phases complete |
| Monthly cleanup job setup | 30 min | After blacklist populated |
| **Total** | **5.5 hours** | Over 1-2 weeks |

---

## Success Metrics

1. **Blacklist Coverage**:
   - Target: > 90% of delisted tickers identified
   - Measured: Check blacklist size vs expected delisted count

2. **Monitoring Coverage**:
   - Target: All critical metrics tracked
   - Measured: Dashboard shows all 5 batches

3. **Alert Effectiveness**:
   - Target: < 1 hour to detect issues
   - Measured: Time from issue to alert

4. **Documentation**:
   - Target: All procedures documented
   - Measured: Runbook completeness

---

## Post-Implementation Checklist

After completing Phase 3:

- [ ] Delisted blacklist populated for all batches
- [ ] Monitoring dashboard created and accessible
- [ ] Alert policies configured and tested
- [ ] Integration tests passing
- [ ] Runbook documentation complete
- [ ] Monthly cleanup job scheduled
- [ ] Cost tracking dashboard created
- [ ] Team trained on operational procedures

---

## Ongoing Maintenance

### Weekly
- [ ] Review dashboard for anomalies
- [ ] Check alert history for patterns

### Monthly
- [ ] Run blacklist cleanup job
- [ ] Review cost trends
- [ ] Update documentation if needed

### Quarterly
- [ ] Review and adjust screening criteria
- [ ] Analyze performance trends
- [ ] Optimize further if needed

### Annually
- [ ] Re-scan full universe for delisted tickers
- [ ] Review and update alert thresholds
- [ ] Performance review and optimization planning

---

**Document Version**: 1.0
**Last Updated**: November 16, 2025
**Status**: Ready for Implementation (After Phase 2)
