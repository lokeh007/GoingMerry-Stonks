# Phase 2 Implementation Guide - Performance Optimization
**Goal**: Reduce batch processing time from ~10.8 hours to ~2 hours (5-8x speedup)

**Estimated Time**: 1-2 hours
**Risk Level**: Medium (requires testing before production deployment)
**Expected Impact**:
- Processing time: 10.8 hours → 2 hours (5.4x faster)
- Cost per run: $2.07 → $0.35 (6x cheaper)
- Eliminate overlap with Smart Money batches

---

## Overview

Phase 2 focuses on **performance optimization** to fix the root cause of slow processing. The main issue is aggressive retry backoff delays that can wait up to 120 seconds per retry, causing the effective processing rate to drop from the expected 3.3s/ticker to 32.45s/ticker (10x slower).

**Root Cause**: Retry backoff configuration in `backend/app/services/yfinance_provider.py`
- Current max_delay: 120 seconds (2 minutes!)
- Current rate_limit_multiplier: 2.5x
- Worst-case retry chain: 300 seconds per ticker

---

## Changes Required

### 1. Reduce Retry Backoff Delays (Primary Fix)

**File**: `backend/app/services/yfinance_provider.py`

**Lines to Change**: 114 and 136

**Current Configuration**:
```python
@adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
def _fetch_ticker_info(self, ticker: yf.Ticker) -> dict:
    """Fetch ticker.info with proactive rate limiting and retry logic."""
    # Token bucket rate limiting
    self.rate_limiter.acquire()
    return ticker.info

@adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
def _fetch_ticker_history(self, ticker: yf.Ticker, **kwargs) -> pd.DataFrame:
    """Fetch ticker.history with proactive rate limiting and retry logic."""
    self.rate_limiter.acquire()
    return ticker.history(**kwargs)
```

**New Configuration** (Optimized):
```python
@adaptive_backoff_with_jitter(max_retries=4, base_delay=1.0, max_delay=30.0, rate_limit_multiplier=1.5)
def _fetch_ticker_info(self, ticker: yf.Ticker) -> dict:
    """Fetch ticker.info with proactive rate limiting and retry logic."""
    # Token bucket rate limiting
    self.rate_limiter.acquire()
    return ticker.info

@adaptive_backoff_with_jitter(max_retries=4, base_delay=1.0, max_delay=30.0, rate_limit_multiplier=1.5)
def _fetch_ticker_history(self, ticker: yf.Ticker, **kwargs) -> pd.DataFrame:
    """Fetch ticker.history with proactive rate limiting and retry logic."""
    self.rate_limiter.acquire()
    return ticker.history(**kwargs)
```

**Changes Explained**:
| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| `max_retries` | 5 | 4 | One less retry attempt (still handles transient errors) |
| `base_delay` | 2.0s | 1.0s | Faster initial retry (less waiting) |
| `max_delay` | 120.0s | 30.0s | **Critical**: Cap at 30 seconds instead of 2 minutes |
| `rate_limit_multiplier` | 2.5x | 1.5x | Less aggressive rate limit backoff |

**Retry Delay Comparison**:

Current (aggressive):
```
Attempt 1: 0s (immediate)
Attempt 2: 0-12s  (avg 6s)
Attempt 3: 0-24s  (avg 12s)
Attempt 4: 0-48s  (avg 24s)
Attempt 5: 0-96s  (avg 48s)
Attempt 6: 0-120s (avg 60s)
---
Total worst case: 300s (5 minutes per ticker!)
```

Optimized:
```
Attempt 1: 0s (immediate)
Attempt 2: 0-3s   (avg 1.5s)
Attempt 3: 0-6s   (avg 3s)
Attempt 4: 0-12s  (avg 6s)
Attempt 5: 0-24s  (avg 12s)
---
Total worst case: 45s (6.7x faster!)
```

---

### 2. Add Defensive Null Checks (Safety Enhancement)

**File**: `backend/jobs/run_daily_screeners.py`

**Method**: `_process_ticker()` (lines 242-297)

**Add null checks before using fetched data**:

```python
def _process_ticker(
    self,
    ticker: str,
    undiscovered_params: Dict[str, Any],
    coiled_spring_params: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """
    Process a single ticker through both screeners with shared data.

    This method fetches fundamental data ONCE and reuses it for both screeners,
    eliminating redundant API calls.

    Args:
        ticker: Stock ticker symbol
        undiscovered_params: Parameters for Undiscovered screener
        coiled_spring_params: Parameters for Coiled Spring screener

    Returns:
        Tuple of (undiscovered_result, coiled_spring_result, api_call_count)
        Results are None if ticker doesn't pass the screener
    """
    api_calls = 0

    try:
        # Fetch shared fundamental data (used by both screeners)
        fundamentals = self.yf_provider.get_fundamentals(ticker)
        api_calls += 1

        # ✅ ADD NULL CHECK HERE
        if fundamentals is None or not isinstance(fundamentals, dict):
            logger.debug(f"No fundamentals data for {ticker}, skipping")
            return None, None, api_calls

        # Evaluate for Undiscovered screener
        undiscovered_result = None
        try:
            analyst_data = self.yf_provider.get_analyst_and_insider_data(ticker)
            api_calls += 1

            # ✅ ADD NULL CHECK HERE
            if analyst_data is None or not isinstance(analyst_data, dict):
                logger.debug(f"No analyst data for {ticker}, skipping Undiscovered")
            else:
                undiscovered_result = self._evaluate_undiscovered(
                    ticker, fundamentals, analyst_data, undiscovered_params
                )
        except Exception as e:
            logger.debug(f"Undiscovered evaluation failed for {ticker}: {e}")

        # Evaluate for Coiled Spring screener (reuses fundamentals!)
        coiled_spring_result = None
        try:
            volatility = self.yf_provider.get_volatility_metrics(ticker)
            api_calls += 1

            # ✅ ADD NULL CHECK HERE
            if volatility is None or not isinstance(volatility, dict):
                logger.debug(f"No volatility data for {ticker}, skipping Coiled Spring")
            else:
                coiled_spring_result = self._evaluate_coiled_spring(
                    ticker, fundamentals, volatility, coiled_spring_params
                )
        except Exception as e:
            logger.debug(f"Coiled Spring evaluation failed for {ticker}: {e}")

        return undiscovered_result, coiled_spring_result, api_calls

    except Exception as e:
        # If fundamentals fail, both screeners fail
        logger.debug(f"Fundamentals fetch failed for {ticker}: {e}")
        return None, None, api_calls
```

**Why This Helps**:
- Prevents `NoneType` errors like the FRGT error reported
- Gracefully handles API timeouts that return None
- Improves stability without affecting performance

---

### 3. Optional: Increase Parallel Workers

**File**: `backend/jobs/run_daily_screeners.py`

**Line**: 950

**Current**:
```python
with ThreadPoolExecutor(max_workers=3) as executor:
```

**Proposed** (Start conservative, can increase later):
```python
with ThreadPoolExecutor(max_workers=6) as executor:
```

**Rationale**:
- More workers = more tickers processed in parallel
- With token bucket rate limiting, this is safe
- Start at 6, monitor for rate limit errors
- Can increase to 8 if no issues

**Risk**: May hit rate limits faster if backoff isn't tuned correctly
**Mitigation**: Test with Batch 1 first, rollback if issues

---

## Implementation Steps

### Step 1: Local Testing (30 minutes)

1. **Make changes to local codebase**:
   ```bash
   cd backend

   # Edit yfinance_provider.py (lines 114, 136)
   # Change retry backoff parameters as specified above

   # Edit run_daily_screeners.py (lines 242-297)
   # Add null checks as specified above
   ```

2. **Run unit tests**:
   ```bash
   cd backend
   pytest tests/test_yfinance_provider.py -v
   pytest tests/test_daily_screeners.py -v
   ```

3. **Test with small batch locally** (optional):
   ```bash
   # Test with representative universe (~100 stocks)
   python backend/jobs/run_daily_screeners.py
   ```

### Step 2: Build and Deploy to GCP (20 minutes)

1. **Build new Docker image**:
   ```bash
   cd backend

   # Build with version tag
   docker build -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 .

   # Also tag as latest (for terraform)
   docker tag us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 \
              us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest
   ```

2. **Push to Artifact Registry**:
   ```bash
   # Authenticate Docker (if not already)
   gcloud auth configure-docker us-east5-docker.pkg.dev

   # Push both tags
   docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0
   docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest
   ```

3. **Update Cloud Run jobs**:
   ```bash
   cd terraform/environments/prod

   # Terraform will automatically use latest tag
   terraform plan
   terraform apply
   ```

   Or manually update specific job:
   ```bash
   gcloud run jobs update prod-regular-screeners-batch-2 \
     --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 \
     --region=us-east5
   ```

### Step 3: Test with Batch 1 First (Safety) (2 hours)

**Why Batch 1?**
- Smallest risk (A-D tickers)
- Runs first (4:30 PM ET)
- Can monitor and rollback before other batches

**Testing Process**:

1. **Manually trigger Batch 1** (don't wait for scheduled run):
   ```bash
   gcloud run jobs execute prod-regular-screeners-batch-1 \
     --region=us-east5 \
     --wait
   ```

2. **Monitor execution in real-time**:
   ```bash
   # Watch logs
   gcloud run jobs executions logs tail \
     --job=prod-regular-screeners-batch-1 \
     --region=us-east5
   ```

3. **Key metrics to watch**:
   - Processing rate (should be ~5-10s per ticker, down from 32.45s)
   - Rate limit errors (should not increase)
   - Completion time (should be ~2 hours, down from 10.8 hours)
   - Error rate (should remain stable or decrease)

4. **Success criteria**:
   - ✅ Completes in < 3 hours (preferably ~2 hours)
   - ✅ No increase in rate limit errors (vs baseline)
   - ✅ No new NoneType errors
   - ✅ Similar or better result counts

### Step 4: Deploy to All Batches (10 minutes)

If Batch 1 test is successful:

1. **Update all regular screener jobs**:
   ```bash
   # Update all batches at once
   for batch in 2 3 4 5; do
     gcloud run jobs update prod-regular-screeners-batch-${batch} \
       --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 \
       --region=us-east5
   done
   ```

2. **Verify updates**:
   ```bash
   gcloud run jobs list --region=us-east5 --filter="name~regular-screeners"
   ```

### Step 5: Monitor Production Runs (24 hours)

Monitor the next scheduled runs (starting 4:30 PM ET):

1. **Check Cloud Run logs**:
   ```bash
   # For specific batch
   gcloud run jobs executions logs tail \
     --job=prod-regular-screeners-batch-2 \
     --region=us-east5
   ```

2. **Check Firestore results**:
   - Navigate to Firebase Console
   - Check `screeners/undiscovered/runs/{date}`
   - Check `screeners/coiled_spring/runs/{date}`
   - Verify `execution_time_seconds` is ~7200 (2 hours) instead of ~39000 (10.8 hours)

3. **Create monitoring dashboard** (optional):
   - Create custom metrics in Cloud Monitoring
   - Track execution time, error rate, throughput
   - Set up alerts for anomalies

---

## Rollback Plan

If issues occur during testing:

### Quick Rollback (Revert to Phase 1)

1. **Revert to previous Docker image**:
   ```bash
   # Find previous working image
   gcloud artifacts docker images list \
     us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners

   # Rollback to previous version (replace with actual version)
   gcloud run jobs update prod-regular-screeners-batch-2 \
     --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.0.0 \
     --region=us-east5
   ```

2. **System will continue running with Phase 1 settings**:
   - 12-hour timeout (allows completion)
   - Slower processing (~10.8 hours)
   - But jobs will complete successfully

### Troubleshooting Common Issues

#### Issue: Rate Limit Errors Increase

**Symptoms**: More "429 Too Many Requests" errors in logs

**Solution**: Backoff is too aggressive, reduce further
```python
# Try even more conservative settings
@adaptive_backoff_with_jitter(max_retries=4, base_delay=1.5, max_delay=45.0, rate_limit_multiplier=1.8)
```

#### Issue: Still Too Slow

**Symptoms**: Processing time is 6-8 hours instead of 2 hours

**Possible causes**:
1. Network issues with Yahoo Finance
2. Not enough parallel workers
3. Database/Firestore bottleneck

**Solutions**:
1. Check Yahoo Finance API status
2. Increase workers to 8 (line 950 in run_daily_screeners.py)
3. Check Firestore write performance

#### Issue: NoneType Errors Still Occurring

**Symptoms**: Errors like "argument of type 'NoneType' is not iterable"

**Solution**: Add more null checks in evaluation methods
- Check `_evaluate_undiscovered()` (line 299-354)
- Check `_evaluate_coiled_spring()` (line 356-408)

---

## Expected Results

### Before Phase 2 (Current State with Phase 1)

| Metric | Value |
|--------|-------|
| Processing rate | 32.45s per ticker |
| Batch completion time | ~10.8 hours |
| Cloud Run cost per run | $2.07 |
| Timeout limit | 12 hours |
| Overlap with Smart Money | Yes (significant) |

### After Phase 2 (Optimized)

| Metric | Value | Improvement |
|--------|-------|-------------|
| Processing rate | ~5-10s per ticker | 3-6x faster |
| Batch completion time | ~2 hours | 5.4x faster |
| Cloud Run cost per run | $0.35 | 6x cheaper |
| Timeout limit | 12 hours (safety net) | Same |
| Overlap with Smart Money | No | Eliminated |

---

## Additional Optimizations (If Needed)

If 2-hour completion is still not achieved:

### Option A: Increase Parallel Workers Further
```python
# Line 950 in run_daily_screeners.py
with ThreadPoolExecutor(max_workers=8) as executor:  # Up from 6
```

### Option B: Optimize Token Bucket Rate Limiter
```python
# In yfinance_provider.py __init__ (line 62)
self.rate_limiter = TokenBucket(
    rate=max_requests_per_minute,
    capacity=max_requests_per_minute * 2,  # Increase capacity for burst
)
```

### Option C: Reduce API Calls Per Ticker
- Cache more aggressively (increase TTL)
- Skip optional metrics for tickers that don't meet basic criteria
- Use batch API calls where possible

---

## Success Metrics

Track these metrics to validate success:

1. **Execution Time** (Primary KPI):
   - Target: < 2 hours per batch
   - Acceptable: 2-4 hours per batch
   - Failure: > 6 hours per batch

2. **Error Rate**:
   - Target: < 5% of tickers fail
   - Acceptable: 5-10% fail rate
   - Failure: > 10% fail rate

3. **Rate Limit Errors**:
   - Target: 0 rate limit errors
   - Acceptable: < 5 rate limit errors per batch
   - Failure: > 10 rate limit errors per batch

4. **Result Quality**:
   - Target: Similar or more stocks passing screeners
   - Acceptable: Within 10% of baseline
   - Failure: > 20% reduction in results

5. **Cost**:
   - Target: < $0.50 per run
   - Acceptable: $0.50-$1.00 per run
   - Failure: > $1.00 per run

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Development | 30 min | Make code changes |
| Local Testing | 30 min | Unit tests, smoke tests |
| Build & Deploy | 20 min | Docker build, push, update jobs |
| Batch 1 Test | 2 hours | Test with single batch |
| Full Deployment | 10 min | Deploy to all batches |
| Monitoring | 24 hours | Watch production runs |
| **Total** | **~4 hours** | Including monitoring |

---

## Post-Implementation

After successful deployment:

1. **Update documentation**:
   - Update `CLAUDE.md` with new expected runtimes
   - Document the optimization in deployment guide
   - Update monitoring dashboards

2. **Adjust schedules** (if needed):
   - With 2-hour runtime, can tighten batch spacing
   - Reduce timeout to 4 hours (2x safety margin)
   - Adjust Smart Money schedules if desired

3. **Proceed to Phase 3**:
   - Pre-populate delisted blacklist
   - Add performance monitoring
   - Set up automated alerts

---

## Questions & Clarifications

Before implementing:

1. **Which batch should we test first?**
   - Recommended: Batch 1 (lowest risk)
   - Alternative: Batch 2 (the one with timeout issues)

2. **Should we update all batches at once or incrementally?**
   - Recommended: Test Batch 1, then update all
   - Alternative: Update one batch per day (slower but safer)

3. **What error rate is acceptable?**
   - Current: ~5-10% tickers fail (404s, no data)
   - Target: Maintain or improve

4. **Should we increase parallel workers immediately or wait?**
   - Recommended: Start at 6, increase to 8 if needed
   - Alternative: Stay at 3, only increase if still slow

---

## Files Modified

1. `backend/app/services/yfinance_provider.py`:
   - Lines 114, 136: Update retry backoff parameters

2. `backend/jobs/run_daily_screeners.py`:
   - Lines 242-297: Add null checks in `_process_ticker()`
   - Line 950 (optional): Increase parallel workers

3. Docker image:
   - New version: `v1.1.0`
   - Tag: `latest`

---

**Document Version**: 1.0
**Last Updated**: November 16, 2025
**Status**: Ready for Implementation
