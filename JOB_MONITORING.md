# Cloud Run Job Monitoring Guide

Real-time monitoring tools for tracking batch screener job performance and making optimization decisions.

## Quick Start

### Monitor Latest Running Job

```bash
# Monitor latest batch 3 job
./scripts/monitor.sh 3

# Monitor latest batch 1 job
./scripts/monitor.sh 1

# Monitor latest smart money batch 2
./scripts/monitor-batch-job.sh --job prod-smart-money-screeners-batch-2
```

### Monitor Specific Execution

```bash
# Monitor by execution ID
./scripts/monitor-batch-job.sh prod-regular-screeners-batch-3-tht7w
```

## What the Report Shows

### Timing Metrics
- **Start Time (EST)**: When the job started in Eastern Time
- **Elapsed Time**: How long it's been running
- **Est. Remaining**: Estimated time to completion
- **Est. Total Runtime**: Total expected runtime

### Progress Metrics
- **Stocks Processed**: Number of tickers processed vs estimated total
- **Last Ticker**: Most recently processed ticker symbol
- **Tickers/Minute**: Processing rate
- **Efficiency**: Performance rating (EXCELLENT, GOOD, SLOW, VERY SLOW)

### API Performance
- **Total API Calls**: Total number of yfinance API calls made
- **API Calls/Minute**: Current API call rate
- **Calls per Ticker**: Average API calls needed per stock
- **Rate Limit Status**: Warning if approaching 50 req/min limit

### Errors & Issues
- **Total Errors**: Number of error entries in logs
- **Delisted Tickers**: Stocks identified as delisted/invalid
- **Top Error Types**: Most common errors

### Recommendations
Automated suggestions based on performance:
- Whether to continue or cancel the job
- Whether to increase/decrease worker count
- Whether to adjust rate limits
- Whether to pre-filter delisted tickers

## Interpreting Results

### Efficiency Ratings

| Rating | Tickers/Min | Action |
|--------|-------------|--------|
| **EXCELLENT** | ≥ 8/min | ✅ Let it continue - optimal performance |
| **GOOD** | 5-8/min | ✅ Let it continue - acceptable performance |
| **SLOW** | 2-5/min | ⚠️ Consider optimization - may want to restart with tuning |
| **VERY SLOW** | < 2/min | ❌ Consider canceling - definitely needs optimization |

### API Rate Guidance

| API Calls/Min | Status | Action |
|---------------|--------|--------|
| < 45/min | ✅ Safe | No action needed |
| 45-50/min | ⚠️ Caution | Monitor closely |
| > 50/min | ❌ Danger | Reduce rate limit or workers |

### Estimated Runtime

**Target Runtime per Batch**: ~2-3 hours

- **< 2 hours**: Excellent - very fast processing
- **2-3 hours**: Good - acceptable for overnight runs
- **3-5 hours**: Slow - consider optimization
- **> 5 hours**: Very Slow - cancel and optimize

## Usage Examples

### Scenario 1: Check if Job is Healthy

```bash
./scripts/monitor.sh 3
```

**Look for:**
- Efficiency: GOOD or EXCELLENT
- API rate: < 45 calls/min
- Estimated total: < 3 hours

**Decision**: If all green, let it continue.

### Scenario 2: Job Running Too Slow

```bash
./scripts/monitor.sh 3
```

**Output shows:**
```
Efficiency:          VERY SLOW
Tickers/Minute:      1.2 tickers/min
Est. Total Runtime:  8h 23m 15s
```

**Decision**: Cancel and optimize:
```bash
# Cancel the job
gcloud run jobs executions cancel prod-regular-screeners-batch-3-tht7w \
  --region=us-east5

# Then optimize and re-run
```

### Scenario 3: Approaching Rate Limit

```bash
./scripts/monitor.sh 3
```

**Output shows:**
```
API Calls/Minute:    52.3 calls/min
⚠️  WARNING: API rate (52.3/min) exceeds safe limit (50/min)
```

**Decision**: Reduce rate limit in code or decrease workers.

### Scenario 4: Check Progress Periodically

```bash
# Check every 10 minutes
watch -n 600 ./scripts/monitor.sh 3
```

Or manually:
```bash
# Check now
./scripts/monitor.sh 3

# Wait 10 minutes, check again
# ... do other work ...

# Check again
./scripts/monitor.sh 3
```

## Optimization Decisions

### When to Let Job Continue
- ✅ Efficiency: GOOD or EXCELLENT
- ✅ API rate: < 45 calls/min
- ✅ Estimated total: < 3 hours
- ✅ Few errors (< 20 delisted tickers)

### When to Cancel and Optimize
- ❌ Efficiency: VERY SLOW
- ❌ Estimated total: > 5 hours
- ❌ API rate: > 50 calls/min (risk of blocking)
- ❌ High error count (> 50 delisted tickers)

### Optimization Actions

**If Too Slow:**
```python
# In run_daily_screeners.py
MAX_WORKERS = 8  # Increase from 6
RATE_LIMIT = 55  # Increase from 50 (be careful!)
```

**If Hitting Rate Limits:**
```python
# In run_daily_screeners.py
MAX_WORKERS = 4  # Decrease from 6
RATE_LIMIT = 45  # Decrease from 50
```

**If Many Delisted Tickers:**
```bash
# Pre-filter delisted tickers
python backend/jobs/populate_delisted_blacklist.py --batch 3 --execute
```

## Canceling a Running Job

```bash
# Cancel specific execution
gcloud run jobs executions cancel prod-regular-screeners-batch-3-tht7w \
  --region=us-east5

# Verify cancellation
gcloud run jobs executions describe prod-regular-screeners-batch-3-tht7w \
  --region=us-east5
```

## Monitoring Multiple Jobs

```bash
# Monitor all running regular screener batches
for i in 1 2 3 4 5; do
  echo "=== Batch $i ==="
  ./scripts/monitor.sh $i 2>/dev/null || echo "Not running"
  echo ""
done
```

## Advanced Usage

### Get Raw Execution Metadata

```bash
gcloud run jobs executions describe prod-regular-screeners-batch-3-tht7w \
  --region=us-east5 \
  --format=json
```

### Get Full Logs

```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=prod-regular-screeners-batch-3" \
  --limit=1000 \
  --format=json
```

### Export Report to File

```bash
./scripts/monitor.sh 3 > /tmp/batch3-report.txt
```

### Continuous Monitoring (Auto-refresh every 5 minutes)

```bash
watch -n 300 ./scripts/monitor.sh 3
```

## Typical Performance Benchmarks

Based on production runs:

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| **Tickers/Min** | > 8 | 5-8 | < 5 |
| **API Calls/Min** | 30-45 | 45-50 | > 50 |
| **Total Runtime** | < 2h | 2-3h | > 3h |
| **Calls/Ticker** | 2.5-3.0 | 3.0-3.5 | > 3.5 |
| **Error Rate** | < 1% | 1-2% | > 2% |

## Troubleshooting

### Script Shows "No executions found"

**Cause**: Job hasn't been triggered yet or job name is wrong.

**Fix**:
```bash
# List all jobs
gcloud run jobs list --region=us-east5

# List executions for specific job
gcloud run jobs executions list \
  --job=prod-regular-screeners-batch-3 \
  --region=us-east5
```

### Script Shows Old/Completed Execution

**Cause**: No currently running execution; showing latest.

**Fix**: Trigger a new execution:
```bash
gcloud run jobs execute prod-regular-screeners-batch-3 --region=us-east5
```

### Logs Are Empty or Incomplete

**Cause**: Logs haven't been ingested yet (takes 30-60 seconds).

**Fix**: Wait 1-2 minutes and run again:
```bash
sleep 120
./scripts/monitor.sh 3
```

### "Efficiency: UNKNOWN"

**Cause**: Not enough data yet (job just started).

**Fix**: Wait 5-10 minutes for meaningful metrics:
```bash
sleep 300
./scripts/monitor.sh 3
```

## Integration with Daily Workflow

### Morning Check (8 AM ET)

```bash
# Check if overnight jobs completed successfully
for i in 1 2 3 4 5; do
  echo "Regular Batch $i:"
  ./scripts/monitor-batch-job.sh --job prod-regular-screeners-batch-$i
done
```

### During Development (Testing New Optimizations)

```bash
# 1. Trigger test batch
gcloud run jobs execute prod-regular-screeners-batch-3 --region=us-east5

# 2. Wait for startup
sleep 120

# 3. Monitor for 15 minutes
./scripts/monitor.sh 3

# 4. Check again
sleep 600
./scripts/monitor.sh 3

# 5. Decide: continue or cancel & optimize
```

## Related Scripts

- **`./build-and-push.sh`**: Build and push Docker images
- **`./scripts/setup-daily-email.sh`**: Set up daily summary emails
- **`backend/jobs/populate_delisted_blacklist.py`**: Pre-filter delisted tickers
- **`backend/jobs/daily_summary_report.py`**: Generate email reports

## Notes

- Logs are stored in `/tmp/batch-audit-<execution-id>/` for debugging
- Script can be run repeatedly without side effects
- EST timezone is used for consistency with scheduler times
- Recommendations are automated but use your judgment

---

**Last Updated**: November 16, 2025
**Maintained By**: GoingMerry-Stonks Team
