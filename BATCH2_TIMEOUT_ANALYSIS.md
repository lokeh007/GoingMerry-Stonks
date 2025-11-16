# Batch 2 Timeout Analysis & Recommendations
**Date**: November 16, 2025
**Issue**: Batch 2 job terminated after 3 hours with only 27.8% completion

---

## Executive Summary

**Critical Finding**: The job was terminated due to Cloud Run's 3-hour timeout limit after processing only 333 of 1,200 tickers (27.8%). At the current processing rate of **32.45 seconds per ticker**, the full batch would require **~10.8 hours** to complete.

**Root Cause**: Aggressive retry backoff combined with network errors and rate limiting is causing 10x slower processing than expected.

**Impact**: Without intervention, Batch 2 (and potentially other batches) cannot complete within the 3-hour window.

---

## Detailed Findings

### 1. Timeout Issue ⏱️

| Metric | Value |
|--------|-------|
| **Job Started** | 10:19:56 PM EST |
| **Job Terminated** | 1:19:59 AM EST (exactly 3 hours) |
| **Tickers Processed** | 333 of 1,200 (27.8%) |
| **Last Ticker** | GDIV (still in G section) |
| **Processing Rate** | 32.45 seconds/ticker |
| **Time Required** | ~10.8 hours (3.6x timeout limit) |
| **Current Timeout** | 10,800 seconds (3 hours) |
| **Max Cloud Run Timeout** | 86,400 seconds (24 hours) |

**Conclusion**: Job needs either performance optimization OR timeout increase to 12+ hours.

---

### 2. Performance Analysis 🔍

**Expected Performance**:
- Rate limit: 55 req/min
- API calls per ticker: 3 (fundamentals + analyst_data + volatility)
- Theoretical max: 55 ÷ 3 = 18.3 tickers/min = **~3.3 seconds/ticker**
- Expected batch time: 1,200 tickers × 3.3s = **~66 minutes (~1.1 hours)**

**Actual Performance**:
- Processing rate: **32.45 seconds/ticker** (10x slower than expected!)
- Actual batch time: 1,200 tickers × 32.45s = **~10.8 hours**

**Performance Gap**: 32.45s ÷ 3.3s = **9.8x slower than expected**

**Why So Slow?**
1. **Aggressive Retry Backoff**: The `adaptive_backoff_with_jitter` decorator has:
   - max_retries: 5
   - base_delay: 2.0 seconds
   - max_delay: 120 seconds (2 minutes!)
   - rate_limit_multiplier: 2.5x

   For rate limit/network errors, retry delays can be:
   - Attempt 2: 0-12 seconds
   - Attempt 3: 0-24 seconds
   - Attempt 4: 0-48 seconds
   - Attempt 5: 0-96 seconds
   - Attempt 6: 0-120 seconds (capped)

2. **Network Errors**: CURL errors (2 occurrences) trigger full retry chains with long waits

3. **NoneType Errors**: Data fetch returning None suggests API timeout issues

4. **Parallel Workers**: Only 3 concurrent workers (conservative, could be higher)

---

### 3. Error Categories 🐛

#### Delisted Stocks (11 tickers) - ⚠️ Non-Critical
These tickers have no price data available (should be blacklisted):

```
FNIGX, FOACW, FRFAF, FSTWF, FTPSF, FVGPY,
GACW, GADA, GAFC, GBNXY, GDEL
```

**Impact**: Minimal (11 tickers × 32.45s = ~6 minutes wasted)

**Solution**: ✅ Script created (`backend/jobs/add_batch2_delisted.py`) to add to blacklist

---

#### NoneType Errors (2 occurrences) - ⚠️ Moderate

**Error**: `argument of type 'NoneType' is not iterable`

**Ticker**: FRGT

**Time**: 12:44:19 AM EST

**Cause**: Data fetch returned `None` instead of expected dict object, then code tried to check `if 'key' in None` which raises TypeError.

**Impact**: Non-fatal (job continued), but indicates API timeout or missing data issues

**Recommendation**: Add defensive null checks before accessing fetched data

**Code Fix Example**:
```python
fundamentals = self.yf_provider.get_fundamentals(ticker)
if fundamentals is None:
    logger.warning(f"No fundamentals data for {ticker}, skipping")
    return None, None, api_calls
# Only proceed if fundamentals is not None
```

---

#### CURL Errors (2 occurrences) - ⚠️ Moderate

**Error**: `Failed to perform, curl: (16)`

**Times**: 12:44:19 AM EST, 01:06:26 AM EST

**Cause**: Transient network/connection issues (likely Yahoo Finance API instability)

**Impact**: Non-fatal (job continued), but each error triggers retry chain with exponential backoff (could add 0-120 seconds per occurrence)

**Recommendation**: Already handled by retry logic; consider reducing max_delay to prevent excessive waits

---

## Recommended Solutions 🛠️

### Quick Wins (Immediate - < 1 hour to implement)

#### 1. ✅ Add Delisted Tickers to Blacklist
**Impact**: Saves ~6 minutes per run
**Effort**: 5 minutes
**Status**: Script ready (`backend/jobs/add_batch2_delisted.py`)

```bash
cd backend
python jobs/add_batch2_delisted.py
```

This will add the 11 delisted tickers to Firestore blacklist. Future runs will automatically skip them.

---

#### 2. 🔧 Increase Cloud Run Job Timeout (Terraform)
**Impact**: Allows current code to complete (10.8 hours > 3 hours)
**Effort**: 10 minutes
**Risk**: Low

**File**: `terraform/modules/scheduled_jobs/main.tf`

**Change**:
```terraform
variable "job_timeout" {
  description = "Job execution timeout in seconds (per batch)"
  type        = number
  default     = 43200  # 12 hours (increased from 3 hours)
  # Max Cloud Run Job timeout is 86400s (24 hours)
}
```

**Deployment**:
```bash
cd terraform/environments/prod
terraform plan
terraform apply
```

**Pros**:
- Simple change
- No code modifications required
- Allows completion at current processing rate

**Cons**:
- Doesn't fix root performance issue
- Uses Cloud Run resources for 12+ hours (higher cost)
- Batch 2 would overlap with Batch 3 schedule (need to adjust schedules)

---

### Medium Wins (1-2 hours to implement)

#### 3. 🚀 Reduce Retry Backoff Delays
**Impact**: Could reduce processing time by 5-8x (bring 32.45s → ~5-10s per ticker)
**Effort**: 30 minutes
**Risk**: Medium (need to balance with avoiding rate limits)

**File**: `backend/app/services/yfinance_provider.py`

**Current**:
```python
@adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
```

**Proposed**:
```python
@adaptive_backoff_with_jitter(max_retries=4, base_delay=1.0, max_delay=30.0, rate_limit_multiplier=1.5)
```

**Changes**:
- `max_retries`: 5 → 4 (one less retry)
- `base_delay`: 2.0s → 1.0s (faster initial retry)
- `max_delay`: 120s → 30s (cap at 30 seconds instead of 2 minutes!)
- `rate_limit_multiplier`: 2.5x → 1.5x (less aggressive rate limit backoff)

**New Retry Schedule** (for rate limit errors):
- Attempt 2: 0-3 seconds (down from 0-12s)
- Attempt 3: 0-6 seconds (down from 0-24s)
- Attempt 4: 0-12 seconds (down from 0-48s)
- Attempt 5: 0-24 seconds (down from 0-96s)

**Deployment**:
```bash
cd backend
# Run tests first
pytest tests/test_yfinance_provider.py -v

# Build and deploy new Docker image
docker build -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 .
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0

# Update Cloud Run job to use new image
gcloud run jobs update prod-regular-screeners-batch-2 \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v1.1.0 \
  --region=us-east5
```

**Pros**:
- Significantly faster processing
- Still handles transient errors
- Reduces Cloud Run costs

**Cons**:
- Need to test carefully to avoid hitting actual rate limits
- May need tuning based on Yahoo Finance API behavior

---

#### 4. 🛡️ Add Defensive Null Checks
**Impact**: Prevents NoneType errors from causing issues
**Effort**: 20 minutes
**Risk**: Low

**File**: `backend/jobs/run_daily_screeners.py`

**Location**: `_process_ticker()` method (line 242-297)

**Add null checks**:
```python
def _process_ticker(
    self,
    ticker: str,
    undiscovered_params: Dict[str, Any],
    coiled_spring_params: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """Process a single ticker through both screeners with shared data."""
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

---

### Long-Term Wins (2-4 hours to implement)

#### 5. 🔀 Split Batch 2 into Sub-Batches
**Impact**: Each sub-batch completes within 3-hour timeout
**Effort**: 2 hours (Terraform + testing)
**Risk**: Medium (complexity)

**Current**: Batch 2 = E-J (~1200 stocks, needs 10.8 hours)

**Proposed**:
- Batch 2A: E-F (~480 stocks, needs ~4.3 hours with current speed, ~26 min optimized)
- Batch 2B: G-H (~480 stocks, needs ~4.3 hours with current speed, ~26 min optimized)
- Batch 2C: I-J (~240 stocks, needs ~2.2 hours with current speed, ~13 min optimized)

**Schedule** (maintain non-overlapping runs):
- Batch 2A: 6:00 PM ET
- Batch 2B: 7:00 PM ET (offset by 1 hour)
- Batch 2C: 8:00 PM ET (offset by 2 hours)

**Files to Modify**:
- `terraform/modules/scheduled_jobs/main.tf` - Add batch-2a, batch-2b, batch-2c
- `backend/app/services/ticker_universe.py` - Add sub-batch logic
- `backend/jobs/run_daily_screeners.py` - Support sub-batch numbers

**Pros**:
- Each sub-batch completes within timeout (even at slow speed)
- Parallel processing potential (if resources allow)
- Fine-grained failure isolation

**Cons**:
- More complex infrastructure
- More Cloud Run jobs to manage (10 → 12 jobs)
- Requires schedule adjustments

---

#### 6. ⚡ Increase Parallel Workers
**Impact**: Could reduce time by 2-3x (if not already rate-limited)
**Effort**: 15 minutes
**Risk**: Medium (may hit rate limits faster)

**File**: `backend/jobs/run_daily_screeners.py`

**Current** (line 950):
```python
with ThreadPoolExecutor(max_workers=3) as executor:
```

**Proposed**:
```python
with ThreadPoolExecutor(max_workers=8) as executor:
```

**Rationale**:
- Current: 3 workers × 55 req/min = potential for 165 req/min (but limited to 55 by rate limiter)
- With proper rate limiting, more workers = more tickers in flight = faster completion
- Need to ensure token bucket rate limiter can handle concurrent requests

**Testing Required**:
- Test with batch 1 (smaller, lower risk)
- Monitor for rate limit errors
- Adjust based on results

---

#### 7. 🎯 Pre-populate Delisted Blacklist
**Impact**: Saves API calls on ALL future runs (not just Batch 2)
**Effort**: 2 hours initial run + monitoring
**Risk**: Low

**Script**: `backend/jobs/populate_delisted_blacklist.py`

**Usage**:
```bash
# Dry run first (check without blacklisting)
python backend/jobs/populate_delisted_blacklist.py --batch 2 --dry-run

# Actual run (add to blacklist)
python backend/jobs/populate_delisted_blacklist.py --batch 2 --rate-limit 50
```

**Process**:
- Scans all tickers in batch 2
- Identifies delisted/invalid tickers (404s, no data)
- Adds to Firestore blacklist automatically
- Future screener runs skip these tickers

**Estimated Time**: ~2 hours for batch 2 (1200 tickers ÷ 50 req/min = 24 min for checks)

**Pros**:
- One-time cost
- Permanent benefit for all future runs
- Can run for all 5 batches proactively

**Cons**:
- Initial time investment
- API usage during scan

---

## Recommended Implementation Plan 🗓️

### Phase 1: Immediate (Today)
**Goal**: Stop the bleeding, allow batch to complete

1. ✅ **Add delisted tickers to blacklist** (5 min)
   ```bash
   python backend/jobs/add_batch2_delisted.py
   ```

2. 🔧 **Increase timeout to 12 hours** (15 min)
   ```bash
   cd terraform/environments/prod
   # Edit main.tf: job_timeout = 43200
   terraform apply
   ```

3. 📅 **Adjust batch schedules** to prevent overlap (10 min)
   - Batch 2: 6:00 PM → 3:00 AM (9 hours)
   - Batch 3: 7:30 PM → adjust to 3:30 AM start
   - etc.

**Expected Outcome**: Batch 2 completes (slow but successful)

---

### Phase 2: Performance Optimization (Next Week)
**Goal**: Reduce processing time from 10.8 hours → ~2 hours

1. 🚀 **Reduce retry backoff delays** (30 min)
   - Implement changes to `yfinance_provider.py`
   - Test with batch 1
   - Deploy to all batches

2. 🛡️ **Add defensive null checks** (20 min)
   - Update `run_daily_screeners.py`
   - Prevents NoneType errors

3. ⚡ **Increase parallel workers** (15 min + testing)
   - Start with 6 workers
   - Monitor rate limits
   - Increase to 8 if no issues

**Expected Outcome**: Processing time reduces to ~2-3 hours per batch

---

### Phase 3: Long-Term Optimization (Next Month)
**Goal**: Proactive maintenance, prevent future issues

1. 🎯 **Pre-populate delisted blacklist** (2 hours)
   - Run for all 5 batches
   - Set up monthly cleanup job

2. 📊 **Add performance monitoring** (1 hour)
   - Track processing rate per batch
   - Alert if rate drops below threshold
   - Dashboard for daily runs

**Expected Outcome**: Stable, fast, reliable screener runs

---

## Risk Assessment ⚠️

| Solution | Risk Level | Mitigation |
|----------|-----------|------------|
| Increase timeout | 🟢 Low | Test with one batch first |
| Reduce backoff | 🟡 Medium | Monitor for rate limit errors, can revert quickly |
| Null checks | 🟢 Low | Defensive programming, improves stability |
| Increase workers | 🟡 Medium | Start conservative (6), increase gradually |
| Split batches | 🟠 High | Complex infrastructure change, test thoroughly |

---

## Cost Analysis 💰

### Current State (Failing)
- Batch 2 runtime: 3 hours (timeout)
- Cloud Run cost: 3 hours × 2 vCPU × $0.00002400/vCPU-second = **$0.52/run**
- **Problem**: Job fails, no results

### With Timeout Increase (Quick Win)
- Batch 2 runtime: 12 hours (completes)
- Cloud Run cost: 12 hours × 2 vCPU × $0.00002400/vCPU-second = **$2.07/run**
- **ROI**: Job succeeds (+100% success rate), costs 4x more

### With Performance Optimization (Best)
- Batch 2 runtime: 2 hours (completes fast)
- Cloud Run cost: 2 hours × 2 vCPU × $0.00002400/vCPU-second = **$0.35/run**
- **ROI**: Job succeeds, costs 33% LESS than current failing run

**Recommendation**: Implement both (timeout increase + performance optimization)
- Short-term: Ensure success
- Long-term: Reduce costs

---

## Next Steps 🎯

### Immediate Actions (You)
1. Review this analysis
2. Approve Phase 1 changes (timeout increase)
3. Test delisted ticker script
4. Monitor tonight's runs

### Development Tasks (Claude Code)
1. Implement Phase 1 (timeout + blacklist)
2. Test Phase 2 optimizations locally
3. Deploy Phase 2 to staging/dev first
4. Monitor and iterate

---

## Monitoring & Validation 📊

### Metrics to Track
1. **Processing rate**: Should increase from 32.45s → ~5-10s per ticker
2. **Completion time**: Should reduce from 10.8 hours → ~2 hours
3. **Error rate**: Should remain stable or decrease
4. **API rate limit hits**: Should not increase significantly

### Success Criteria
- ✅ Batch 2 completes within timeout
- ✅ Processing rate < 10 seconds per ticker
- ✅ Error rate < 5%
- ✅ No increase in rate limit errors

---

## Questions & Clarifications ❓

1. **Do you want to proceed with Phase 1 (timeout increase) immediately?**
   - This will allow batch 2 to complete tonight, even if slowly

2. **Should we implement Phase 2 (performance optimization) before or after verifying Phase 1 works?**
   - Recommended: Phase 1 first (safety), then Phase 2 (speed)

3. **Are you willing to accept higher Cloud Run costs ($2.07 vs $0.35 per run) temporarily?**
   - This is the trade-off for timeout increase vs optimization

4. **Should we split Batch 2 into sub-batches (Phase 3) or is performance optimization sufficient?**
   - Splitting adds complexity but provides insurance

---

## Appendix: Technical Details 🔧

### Cloud Run Job Timeout Limits
- **Service timeout**: 3,600 seconds (1 hour) max
- **Job timeout**: 86,400 seconds (24 hours) max ✅ We can use this!
- **Current setting**: 10,800 seconds (3 hours)
- **Recommended**: 43,200 seconds (12 hours) for safety

### Retry Backoff Math
**Current aggressive backoff** (max_delay=120s, rate_limit_multiplier=2.5):
```
Attempt 1: 0s (immediate)
Attempt 2: 0-12s  (2.0 * 2^0 * 2.5 = 5.0, jitter: 0-5s)
Attempt 3: 0-24s  (2.0 * 2^1 * 2.5 = 10.0, jitter: 0-10s)
Attempt 4: 0-48s  (2.0 * 2^2 * 2.5 = 20.0, jitter: 0-20s)
Attempt 5: 0-96s  (2.0 * 2^3 * 2.5 = 40.0, jitter: 0-40s)
Attempt 6: 0-120s (2.0 * 2^4 * 2.5 = 80.0, capped at 120s max_delay)
Total worst case: 300s (5 minutes) per ticker!
```

**Proposed optimized backoff** (max_delay=30s, rate_limit_multiplier=1.5):
```
Attempt 1: 0s (immediate)
Attempt 2: 0-3s   (1.0 * 2^0 * 1.5 = 1.5, jitter: 0-1.5s)
Attempt 3: 0-6s   (1.0 * 2^1 * 1.5 = 3.0, jitter: 0-3s)
Attempt 4: 0-12s  (1.0 * 2^2 * 1.5 = 6.0, jitter: 0-6s)
Attempt 5: 0-24s  (1.0 * 2^3 * 1.5 = 12.0, jitter: 0-12s)
Total worst case: 45s per ticker (6.7x faster!)
```

---

**Document Version**: 1.0
**Last Updated**: November 16, 2025
**Author**: Claude Code Analysis
