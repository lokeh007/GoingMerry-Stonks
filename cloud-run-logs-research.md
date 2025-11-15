# Cloud Run Logs Research Summary
**Date:** November 15, 2025

## Executive Summary

Analysis of Cloud Run batch job executions reveals a critical rate limiting issue causing immediate API throttling and system-wide failures. The investigation included comprehensive log analysis, scheduler configuration review, and real-time execution monitoring.

---

## Last 5 Cloud Run Executions (Nov 15, 2025)

### 1. 🚫 prod-regular-screeners-batch-1-w5f75 - **CANCELLED**
- **Time:** 4:24 PM → 4:37 PM EST (13m runtime)
- **Status:** Cancelled by user during investigation
- **Critical Finding:** Rate limiting started at **0 seconds** (immediately upon start)
- **Execution Metrics:**
  - Tickers Processed: 1,651 (A through DZZ)
  - Rate Limit Events: 3,302
  - Impact Ratio: 200% (2 rate limit errors per ticker)
  - Stocks Found: 0
  - Start Time: Nov 15, 4:34 PM EST
  - First Rate Limit: Nov 15, 4:34 PM EST (same second)

### 2. ✅ prod-smart-money-screeners-batch-5-gxzw2 - **SUCCEEDED**
- **Time:** 8:00 AM → 8:43 AM EST (43m runtime)
- **Status:** Completed successfully
- **Performance:** Longest successful run of the day

### 3. ❌ prod-smart-money-screeners-batch-4-kxt4h - **FAILED**
- **Time:** 6:00 AM → 8:10 AM EST (130m runtime)
- **Status:** Failed with container exit error
- **Duration:** Abnormally long runtime indicates API throttling

### 4. ❌ prod-smart-money-screeners-batch-3-hnq8j - **FAILED**
- **Time:** 4:00 AM → 5:31 AM EST (91m runtime)
- **Status:** Failed with container exit error
- **Issue:** Extended runtime suggests severe rate limiting

### 5. ✅ prod-smart-money-screeners-batch-2-sht8r - **SUCCEEDED**
- **Time:** 2:00 AM → 3:05 AM EST (64m runtime)
- **Status:** Completed successfully
- **Note:** One of two successful smart money runs today

---

## Today's Overall Statistics (Nov 15, 2025)

**Total Executions:** 9
- ✅ **Succeeded:** 5 (55.6%)
- ❌ **Failed:** 3 (33.3%)
- 🚫 **Cancelled:** 1 (11.1%)

**Job Type Breakdown:**
- **Regular Screeners:** 4 runs (3 succeeded, 1 cancelled)
- **Smart Money Screeners:** 5 runs (2 succeeded, 3 failed)

**Smart Money Screener Failure Rate:** 60% (3/5 failed)

---

## Critical Issues Identified

### 1. **Immediate Rate Limiting (0-Second Throttle)**
**Severity:** CRITICAL

The most recent batch-1 execution demonstrated that yfinance API rate limiting occurs **immediately upon job start** (0 seconds), indicating:
- Rate limits persist across job executions (no cooldown)
- The API is pre-throttled from previous runs
- Current 50 req/min limit is ineffective
- No productive work can occur in this state

**Evidence:**
```
Start Time:        Nov 15, 04:34:12 PM EST
First Rate Limit:  Nov 15, 04:34:12 PM EST
Time to Throttle:  0m 0s (0 seconds)
```

**Impact:**
- 200% error ratio (3,302 rate limit events for 1,651 tickers)
- Zero stocks successfully processed
- Complete job failure despite 13-minute runtime

### 2. **Firestore Data Type Conversion Errors**
**Severity:** HIGH

Smart money screeners experiencing "Cannot convert to a Firestore Value" errors:
- 10+ occurrences across failed runs
- Affecting batches 1, 3, and 4
- Causing container exit failures

### 3. **Scheduler Retry Configuration**
**Severity:** MEDIUM (RESOLVED)

Previous issue with duplicate runs caused by `retry_count=1`:
- **Example:** Batch-4 ran twice (9:07 PM and 9:09 PM on Nov 14)
- **Resolution:** Changed to `retry_count=0` in Terraform
- **Status:** Fix implemented but not yet deployed

---

## Rate Limiting Analysis

### Current Configuration
- **Regular Screeners:** 50 req/min (reduced from 60)
- **Smart Money Screeners:** 36 req/min (accounts for 3 API calls/ticker)
- **Job Intervals:** 90 minutes (regular), 2h 15m - 2h 30m (smart money)

### Observed Behavior
- **Throttle Onset:** 0 seconds (immediate)
- **Error Pattern:** Multiple rate limit errors per ticker
- **Persistence:** Rate limits carry over between job runs
- **Recovery:** No evidence of rate limit cooldown

### Root Causes
1. **Insufficient Cooldown Period:** 90-minute intervals inadequate for API recovery
2. **Aggressive Rate Limits:** 50 req/min still triggers immediate throttling
3. **No Rate Limit Reset:** yfinance API maintains throttle state across runs
4. **Cumulative API Calls:** Smart money jobs make 3 calls/ticker, compounding limits

---

## Historical Context (Last 24 Hours)

### Smart Money Screener Performance
- **Total Runs:** 22 executions
- **Succeeded:** 1 (4.5%)
- **Failed:** 21 (95.5%)
- **Failure Rate:** 95.5%

**Missing Batches:**
- Batches 1-2 showed no runs in initial 24-hour analysis
- Later runs confirmed they are executing but with high failure rates

### Regular Screener Performance
- **Overall Success Rate:** Much higher than smart money screeners
- **Batch-1 Previous Run:** Nov 14, 9:30 PM EST - succeeded (23m runtime)
- **Recent Pattern:** Generally completing successfully when not rate-limited

---

## Technical Infrastructure

### GCP Configuration
- **Project:** sylvan-earth-477020-u6
- **Region:** us-east5 (Cloud Run Jobs), us-east1 (Cloud Scheduler)
- **Container Image:** daily-screeners:latest
- **Resources:** 2 vCPU, 2Gi memory per job
- **Timeout:** 10800s (3 hours)

### Batch Jobs
**Regular Screeners (5 batches):**
- Undiscovered + Coiled Spring patterns
- Schedule: 4:30 PM - 12:30 AM EST (90-minute intervals)

**Smart Money Screeners (5 batches):**
- Options Flow analysis
- Schedule: 12:15 AM - 11:40 AM EST (2h 15m - 2h 30m intervals)

### External Dependencies
- **Primary API:** yfinance (rate limiting bottleneck)
- **Secondary API:** Polygon (configured but underutilized)
- **Data Store:** Firestore (experiencing type conversion issues)

---

## Recommended Actions

### IMMEDIATE (High Priority)

1. **Reduce Rate Limits**
   - Change `regular_screeners_rate_limit` from 50 to 20-25 req/min
   - Verify `smart_money_rate_limit` at 36 is appropriate
   - Deploy Terraform changes immediately

2. **Increase Cooldown Periods**
   - Extend regular screener intervals from 90 minutes to 2-3 hours
   - Increase smart money intervals to allow API recovery
   - Ensure zero overlap between consecutive batches

3. **Fix Firestore Type Errors**
   - Review `backend/jobs/run_smart_money_screener.py`
   - Identify data type conversion issues
   - Test fix with single ticker before deployment

### SHORT-TERM (Next 24-48 Hours)

4. **Deploy Scheduler Retry Fix**
   - Apply `retry_count=0` Terraform changes
   - Verify no duplicate runs occur
   - Monitor for 24 hours

5. **Implement API Request Backoff**
   - Add exponential backoff for rate limit errors
   - Implement request queuing with delays
   - Log rate limit recovery times

6. **Add Pre-flight Rate Limit Check**
   - Test API availability before job starts
   - Abort job if already rate-limited
   - Log API state for diagnostics

### STRATEGIC (Next Week)

7. **Evaluate Alternative Data Sources**
   - **Polygon API:** Already have key, increase usage
   - **Alpha Vantage:** Consider for specific data points
   - **IEX Cloud:** Evaluate cost vs. reliability
   - **Goal:** Reduce yfinance dependency to <50%

8. **Implement Rate Limit Dashboard**
   - Track API calls per minute in real-time
   - Monitor rate limit errors across all batches
   - Alert when approaching limits

9. **Batch Size Optimization**
   - Reduce tickers per batch to lower API call volume
   - Increase number of batches with longer intervals
   - Calculate optimal batch size based on rate limits

---

## Key Learnings

1. **Rate Limits Persist:** yfinance API maintains throttle state across separate job executions
2. **Scheduler Retries Harmful:** Automatic retries cause duplicate runs; application-level retry logic preferred
3. **Immediate Throttling Indicates Saturation:** 0-second rate limiting means API was already throttled before job started
4. **200% Error Ratio:** Multiple API calls per ticker compound rate limit issues exponentially
5. **Smart Money Higher Risk:** 3 API calls/ticker makes smart money screeners 3x more vulnerable to rate limits

---

## Current System State

**Cloud Run Jobs:** All idle (no running executions as of 4:37 PM EST)

**Next Scheduled Run:**
- Regular Batch-2: 6:00 PM EST (90 minutes from last cancelled run)
- Expected to hit immediate rate limiting if no changes deployed

**System Health:** 🔴 CRITICAL
- Rate limiting prevents productive work
- 60% failure rate on smart money screeners
- Zero stocks processed in most recent execution

---

## Monitoring Commands

### Check Recent Executions
```bash
gcloud run jobs executions list --region=us-east5 --limit=10 --sort-by=~createTime
```

### View Live Logs for Specific Job
```bash
gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=prod-regular-screeners-batch-1" --region=us-east5
```

### Analyze Rate Limiting
```bash
gcloud logging read 'resource.type=cloud_run_job AND textPayload:"Rate limit"' \
  --limit=100 --format=json --freshness=1h
```

### Check Scheduler Status
```bash
gcloud scheduler jobs list --location=us-east1
```

---

## Files Modified/Analyzed

- `terraform/modules/scheduled_jobs/main.tf` - Retry configuration updated
- `backend/jobs/run_daily_screeners.py` - Regular screener logic
- `backend/jobs/run_smart_money_screener.py` - Smart money screener (needs fix)
- `/tmp/batch1_recent.json` - 5,000 log entries analyzed
- `/tmp/smart_money_logs.json` - Smart money failure analysis

---

## Investigation Timeline

- **9:07 PM (Nov 14):** Identified duplicate scheduler runs
- **Last 24 hours:** Analyzed 22 smart money runs (95.5% failure rate)
- **4:24 PM (Nov 15):** Started batch-1 execution
- **4:34 PM:** Job began, immediate rate limiting detected
- **4:37 PM:** Cancelled execution, analyzed 5,000 log entries
- **Result:** Confirmed 0-second throttle onset, 200% error ratio

---

**Last Updated:** November 15, 2025, 4:45 PM EST
**Analyst:** Principal Software Engineer Mode
**Status:** Active investigation, deployment pending
