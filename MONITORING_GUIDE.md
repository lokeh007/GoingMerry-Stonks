# 📊 Batch Screener Monitoring Guide

Comprehensive monitoring solution for the daily batch screener jobs.

## Current Alarms (3)

| Alarm | Condition | Status |
|-------|-----------|--------|
| **High Error Rate** | API >5% errors | ✅ Enabled |
| **High Latency** | P95 >2 seconds | ✅ Enabled |
| **Database High Connections** | >80% capacity | ✅ Enabled |

**Notifications**: brian.boatright@gmail.com

---

## Recommended Monitoring (4 Layers)

### Layer 1: Job Execution Alarms

**What**: Alerts when batch jobs fail to complete successfully

**Alarms**:
1. **Regular Screeners Failed** - Triggers when any of the 5 regular screener batches fail
2. **Smart Money Screeners Failed** - Triggers when any of the 5 smart money batches fail

**Threshold**: Any failed execution (> 0 failures)

**Benefit**: Immediate notification of job failures so you can investigate

---

### Layer 2: Log-Based Metrics (Error Tracking)

**What**: Tracks different types of errors from job logs

**Metrics Created**:
1. **screener_data_errors** - 404s, no data, delisted tickers (expected errors)
2. **screener_rate_limit_errors** - Rate limiting from yfinance (needs attention)
3. **screener_undiscovered_count** - Stocks found by Undiscovered screener
4. **screener_coiled_spring_count** - Stocks found by Coiled Spring screener
5. **screener_smart_money_count** - Stocks found by Smart Money screener

**Alarms**:
- **High Data Error Rate** - >50 data errors per hour (may indicate bad ticker universe)
- **Rate Limiting Issues** - >10 rate limit errors per hour (need to slow down)

**Benefit**:
- Distinguish between expected errors (delisted tickers) and problems (rate limits)
- Track screener effectiveness over time

---

### Layer 3: Monitoring Dashboard

**What**: Visual dashboard showing job health and metrics

**Metrics Displayed**:
- Job execution success rate (last 7 days)
- Stocks discovered per screener (daily trend)
- Error rates by type (data vs rate limit)
- Execution duration (detect slowdowns)
- Blacklist growth (delisted ticker tracking)

**Access**: Cloud Console → Monitoring → Dashboards

**Benefit**: At-a-glance view of system health

---

### Layer 4: Daily Summary Report

**What**: Automated email report sent daily at 11 AM ET

**Report Contents**:
```
📊 Daily Screener Report - 2025-11-15

Summary:
  • Stocks Found: 45
  • Total Screened: 6,000
  • Total Errors: 12

Screener Results:
  • Undiscovered: 18 stocks (5,989 screened, 11 not found, 0 errors)
  • Coiled Spring: 15 stocks (5,989 screened, 11 not found, 0 errors)
  • Smart Money: 12 stocks (5,989 screened, 11 not found, 0 errors)

Job Execution:
  • Regular Screeners: 5/5 batches successful ✓
  • Smart Money Screeners: 5/5 batches successful ✓

Blacklist:
  • Total Blacklisted: 150 tickers
  • Added Yesterday: 5
  • Error Types: {no_data: 150}
```

**Benefit**: Daily audit trail + early warning system

---

## Setup Instructions

### Quick Setup (Recommended)

Run the automated setup script:

```bash
# Make script executable
chmod +x scripts/setup-batch-monitoring.sh

# Run setup
./scripts/setup-batch-monitoring.sh
```

**What it creates**:
- ✅ 4 alerting policies
- ✅ 5 log-based metrics
- ✅ Email notifications configured
- ✅ Auto-close for transient issues

**Time**: ~2 minutes

---

### Daily Summary Report Setup

**Option 1: Manual Testing**

```bash
# Generate report for yesterday (no email)
python3 backend/jobs/daily_summary_report.py --no-send

# View report
open /tmp/screener_report_2025-11-15.html
```

**Option 2: Send Test Email**

```bash
# Set up Gmail App Password (one-time)
# 1. Go to: https://myaccount.google.com/apppasswords
# 2. Create app password for "GoingMerry Screeners"
# 3. Set environment variable:
export GMAIL_SENDER="your-email@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Send test report
python3 backend/jobs/daily_summary_report.py --email brian.boatright@gmail.com
```

**Option 3: Automated Daily (Cloud Scheduler)**

```bash
# Create Cloud Run Job for daily report
gcloud run jobs create prod-daily-summary-report \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:latest \
  --region=us-east5 \
  --set-env-vars=GMAIL_SENDER=your-email@gmail.com \
  --set-secrets=GMAIL_APP_PASSWORD=gmail-app-password:latest \
  --max-retries=2 \
  --task-timeout=5m \
  --command=python3,backend/jobs/daily_summary_report.py

# Schedule to run daily at 11 AM ET
gcloud scheduler jobs create http prod-daily-summary-scheduler \
  --location=us-east5 \
  --schedule="0 11 * * *" \
  --time-zone="America/New_York" \
  --uri="https://us-east5-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/sylvan-earth-477020-u6/jobs/prod-daily-summary-report:run" \
  --http-method=POST \
  --oauth-service-account-email=prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com
```

---

## Viewing Monitoring Data

### View Alarms

```bash
# List all alarms
gcloud alpha monitoring policies list --project=sylvan-earth-477020-u6

# View specific alarm
gcloud alpha monitoring policies describe POLICY_ID --project=sylvan-earth-477020-u6
```

**Console**: https://console.cloud.google.com/monitoring/alerting?project=sylvan-earth-477020-u6

### View Metrics

```bash
# List log-based metrics
gcloud logging metrics list --project=sylvan-earth-477020-u6

# Query metric data
gcloud monitoring time-series list \
  --filter='metric.type="logging.googleapis.com/user/screener_data_errors"' \
  --project=sylvan-earth-477020-u6
```

**Console**: https://console.cloud.google.com/logs/metrics?project=sylvan-earth-477020-u6

### View Job Execution History

```bash
# List recent executions for a job
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=10

# Get execution details
gcloud run jobs executions describe EXECUTION_NAME \
  --region=us-east5

# View execution logs
gcloud run jobs logs read prod-regular-screeners-batch-1 \
  --region=us-east5 \
  --limit=100
```

**Console**: https://console.cloud.google.com/run/jobs?project=sylvan-earth-477020-u6

---

## Alert Interpretation

### 🚨 "Batch Jobs - Regular Screeners Failed"

**Meaning**: One or more regular screener batches (Undiscovered + Coiled Spring) failed

**Action**:
1. Check which batch failed:
   ```bash
   gcloud run jobs executions list --job=prod-regular-screeners-batch-1 --region=us-east5 --limit=5
   ```
2. View failure logs:
   ```bash
   gcloud run jobs logs read prod-regular-screeners-batch-1 --region=us-east5 --limit=200
   ```
3. Common causes:
   - Rate limiting (see "Rate Limiting Issues" alarm)
   - Database connection timeout
   - Memory/CPU limits exceeded
   - Firestore write errors

### 🚨 "Batch Jobs - High Data Error Rate"

**Meaning**: >50 tickers returning "no data" or 404 errors per hour

**Action**:
1. Check if ticker universe source changed
2. Verify yfinance API is working:
   ```bash
   python3 -c "import yfinance as yf; print(yf.Ticker('AAPL').info)"
   ```
3. Review blacklist statistics:
   ```bash
   python3 backend/test_delisted_cache.py
   ```
4. Consider running delisted ticker scan:
   ```bash
   python3 backend/jobs/populate_delisted_blacklist.py --batch 1
   ```

### 🚨 "Batch Jobs - Rate Limiting Issues"

**Meaning**: >10 rate limit errors from yfinance per hour

**Action**:
1. Check current rate limit settings:
   ```bash
   grep "max_requests_per_minute" backend/jobs/run_daily_screeners.py
   grep "max_requests_per_minute" backend/jobs/run_smart_money_screener.py
   ```
2. Reduce rate limit:
   - Regular screeners: Currently 55 req/min → reduce to 45 req/min
   - Smart money: Currently 50 req/min → reduce to 40 req/min
3. Monitor adaptive backoff in logs:
   ```bash
   gcloud run jobs logs read prod-regular-screeners-batch-1 --region=us-east5 | grep -i "rate limit"
   ```

---

## Metrics Reference

### Job Execution Metrics (Built-in)

| Metric | Description | Unit |
|--------|-------------|------|
| `run.googleapis.com/job/completed_execution_count` | Completed executions (success/failure) | count |
| `run.googleapis.com/job/billable_time` | Execution duration | seconds |
| `run.googleapis.com/request_count` | API requests to Cloud Run | count |

### Custom Log-Based Metrics

| Metric | Description | Filter |
|--------|-------------|--------|
| `screener_data_errors` | 404, no data, delisted | `message=~".*404.*"` |
| `screener_rate_limit_errors` | Rate limiting errors | `message=~".*rate limit.*"` |
| `screener_undiscovered_count` | Stocks found (Undiscovered) | Extract from log |
| `screener_coiled_spring_count` | Stocks found (Coiled Spring) | Extract from log |
| `screener_smart_money_count` | Stocks found (Smart Money) | Extract from log |

---

## Cost Estimate

**Monitoring Costs** (approximate):
- Alerting policies: **Free** (first 100 policies)
- Log-based metrics: **Free** (first 50 metrics)
- Email notifications: **Free**
- Log ingestion: **$0.50-$1.00/day** (based on log volume)
- Metric data: **$0.01-$0.05/day** (minimal queries)

**Total**: **~$15-30/month** (mostly log storage)

---

## Maintenance

### Weekly
- Review daily summary reports
- Check for recurring errors in blacklist

### Monthly
- Review alerting policies (any false positives?)
- Archive old execution logs (>30 days)
- Clean up expired blacklist entries:
  ```bash
  python3 -c "from app.services.delisted_ticker_cache import DelistedTickerCache; cache = DelistedTickerCache(); cache.cleanup_expired_entries()"
  ```

### Quarterly
- Review metric retention (default: 30 days)
- Evaluate if additional monitoring needed
- Update thresholds based on observed patterns

---

## Troubleshooting

### "No data in metrics dashboard"

**Cause**: Log-based metrics not extracting data correctly

**Fix**:
1. Verify logs are being generated:
   ```bash
   gcloud logging read "resource.type=cloud_run_job" --limit=10 --project=sylvan-earth-477020-u6
   ```
2. Test metric filter:
   ```bash
   gcloud logging read 'jsonPayload.message=~".*stocks passed.*"' --limit=5
   ```
3. Re-create metric with correct filter

### "Alerts not being received"

**Cause**: Notification channel misconfigured

**Fix**:
1. Verify email address:
   ```bash
   gcloud alpha monitoring channels list --project=sylvan-earth-477020-u6
   ```
2. Check spam folder
3. Test notification:
   ```bash
   gcloud alpha monitoring policies test POLICY_ID --project=sylvan-earth-477020-u6
   ```

### "Daily report emails not sending"

**Cause**: Gmail App Password not set or expired

**Fix**:
1. Regenerate Gmail App Password: https://myaccount.google.com/apppasswords
2. Update secret:
   ```bash
   echo -n "xxxx xxxx xxxx xxxx" | gcloud secrets versions add gmail-app-password --data-file=-
   ```
3. Test manually:
   ```bash
   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   python3 backend/jobs/daily_summary_report.py --email brian.boatright@gmail.com
   ```

---

## Next Steps

1. **Set up monitoring** (5 minutes):
   ```bash
   ./scripts/setup-batch-monitoring.sh
   ```

2. **Test daily report** (5 minutes):
   ```bash
   python3 backend/jobs/daily_summary_report.py --no-send
   open /tmp/screener_report_*.html
   ```

3. **Deploy to production** (optional):
   - Build new images with monitoring code
   - Deploy jobs
   - Monitor for 24 hours

4. **Review first report**:
   - Check metrics accuracy
   - Verify alarm thresholds
   - Adjust as needed

---

**Questions?** See logs or create an issue in the repository.

**Last Updated**: 2025-11-15
