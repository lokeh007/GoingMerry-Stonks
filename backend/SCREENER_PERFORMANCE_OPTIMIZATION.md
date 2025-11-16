# Screener Performance Optimization Guide

This document tracks performance optimizations for the batch screener jobs (`run_daily_screeners.py` and `run_smart_money_screener.py`).

---

## Performance Baseline

**Target**: Process ~1200 stocks in 90 minutes (13-14 tickers/min)

**Current Performance** (as of November 16, 2025):
- **Before Tier 1**: 2.16 tickers/min (9.3 hours total)
- **After Tier 1**: TBD (testing in progress)

**Key Metrics**:
- API Calls per Ticker: ~3 calls (fundamentals + analyst/volatility data)
- Rate Limit: 60 req/min (yfinance free tier)
- Configured Limit: 58 req/min (97% of max)
- Workers: 6 concurrent threads

---

## ✅ Tier 1 Optimizations (IMPLEMENTED)

**Status**: Deployed November 16, 2025
**Expected Impact**: 10-20% improvement (2.4-2.6 tickers/min, ~8 hours total)
**Note**: Tier 1 changes are conservative rate-limit optimizations, not algorithmic improvements

### 1. Reduce Token Bucket Sleep Interval
**File**: `backend/app/services/rate_limiter.py:132`

**Change**:
```python
# Before
time.sleep(min(sleep_time, 0.1))  # Sleep max 100ms at a time

# After
time.sleep(min(sleep_time, 0.01))  # Sleep max 10ms at a time
```

**Rationale**:
- With 6 workers, 100ms sleep intervals create significant idle time
- Reducing to 10ms allows workers to acquire tokens 10x faster
- Still prevents busy-waiting while minimizing blocking overhead

**Risk**: Low - No impact on rate limiting logic

---

### 2. Increase Burst Capacity
**File**: `backend/app/services/yfinance_provider.py:71`

**Change**:
```python
# Before
capacity=max_requests_per_minute,  # 55 tokens

# After
capacity=max_requests_per_minute * 2,  # 116 tokens (2x burst)
```

**Rationale**:
- Allows workers to "bank" tokens during idle periods
- Reduces blocking when multiple workers need tokens simultaneously
- Better utilizes API capacity during burst activity

**Risk**: Low - Token refill rate unchanged, just allows burst capacity

---

### 3. Increase Rate Limit
**File**: `backend/jobs/run_daily_screeners.py:86`

**Change**:
```python
# Before
YFinanceProvider(max_requests_per_minute=55)  # 91% of limit

# After
YFinanceProvider(max_requests_per_minute=58)  # 97% of limit
```

**Rationale**:
- Previous setting was conservative (91.7% utilization)
- 58 req/min provides better throughput while still having safety margin (97% utilization)

**Risk**: Low - Still below 60 req/min hard limit

---

## 🔄 Tier 2 Optimizations (RECOMMENDED NEXT)

**Status**: Not implemented
**Expected Impact**: 2-3x improvement (4-6 tickers/min, ~4 hours total)
**Implementation Effort**: Medium (2-3 hours)

### 4. Increase Worker Count
**File**: `backend/jobs/run_daily_screeners.py:965`

**Proposed Change**:
```python
# Current
with ThreadPoolExecutor(max_workers=6) as executor:

# Recommended
with ThreadPoolExecutor(max_workers=10) as executor:
```

**Rationale**:
- Current: 6 workers × 3 API calls = 18 concurrent requests (theoretical)
- Actual: Workers spend time blocked on I/O, not fully utilizing capacity
- With 10 workers, can maintain higher API utilization
- 10 workers × 58 req/min = ~5.8 req/sec (well within capacity)

**Testing Plan**:
1. Test with 8 workers first to validate improvement
2. If successful, increase to 10 workers
3. Monitor API rate limit errors in logs

**Risk**: Medium
- More threads = more memory usage (~10MB per worker)
- Potential for increased rate limit hits if burst too aggressive
- Monitor Cloud Run memory usage

**Rollback**: Easy - just revert worker count

---

### 5. Worker-Level Token Batching
**File**: `backend/jobs/run_daily_screeners.py:242-312` (in `_process_ticker()`)

**Proposed Change**:
```python
def _process_ticker(self, ticker: str, undiscovered_params, coiled_spring_params):
    """Process a single ticker through both screeners with shared data."""

    # PRE-ACQUIRE 3 tokens for all API calls this ticker needs
    self.yf_provider.rate_limiter.acquire(tokens=3, blocking=True)

    api_calls = 0
    try:
        # Fetch fundamental data (NO token acquisition - already have it)
        fundamentals = self._fetch_without_rate_limit(ticker, 'fundamentals')
        api_calls += 1

        # Fetch analyst data (NO token acquisition)
        analyst_data = self._fetch_without_rate_limit(ticker, 'analyst')
        api_calls += 1

        # Fetch volatility data (NO token acquisition)
        volatility = self._fetch_without_rate_limit(ticker, 'volatility')
        api_calls += 1

        # ... rest of processing logic ...

    except Exception as e:
        # If error occurs, we've already consumed the tokens
        # This is acceptable - rate limiting is about average rate
        logger.debug(f"Error processing {ticker}: {e}")
        return None, None, api_calls
```

**New Helper Method**:
```python
def _fetch_without_rate_limit(self, ticker: str, data_type: str):
    """
    Fetch data WITHOUT acquiring rate limit tokens.

    NOTE: Caller MUST pre-acquire tokens before calling this method!
    """
    ticker_obj = self.yf_provider._get_ticker(ticker)

    if data_type == 'fundamentals':
        # Call ticker.info directly (skip rate limiter wrapper)
        return ticker_obj.info
    elif data_type == 'analyst':
        # Fetch analyst data without rate limiting
        return self._extract_analyst_data(ticker_obj)
    elif data_type == 'volatility':
        # Fetch volatility without rate limiting
        return self._extract_volatility_data(ticker_obj)
```

**Rationale**:
- **Current**: Each API call acquires 1 token = 3 lock acquisitions per ticker
- **Proposed**: Pre-acquire 3 tokens = 1 lock acquisition per ticker
- **Impact**: Reduces lock contention by 67% (3 acquisitions → 1)
- Workers spend less time waiting for locks
- More predictable token consumption

**Testing Plan**:
1. Add detailed logging to track token acquisition timing
2. Test with 50 tickers to verify no rate limit errors
3. Compare execution time vs. current implementation
4. Monitor for any unexpected API errors

**Risk**: Medium-High
- More complex code logic
- If ticker processing fails early, tokens are wasted (but this is rare)
- Need careful testing to ensure no race conditions

**Alternatives**:
- **Option A**: Pre-acquire only 2 tokens (fundamentals + analyst), fetch volatility separately
- **Option B**: Use token reservation system instead of pre-acquisition

**Rollback**: Medium difficulty - requires code revert and testing

---

## 🚀 Tier 3 Optimizations (FUTURE)

**Status**: Not implemented
**Expected Impact**: 6-7x improvement (12-15 tickers/min, ~1.5 hours total)
**Implementation Effort**: High (1-2 weeks)
**Note**: To exceed these targets, would need to reduce API calls per ticker or upgrade to paid API tier

### 6. Migrate to AsyncIO + aiohttp
**Files**: Entire `yfinance_provider.py` and `run_daily_screeners.py`

**Proposed Architecture**:
```python
import asyncio
import aiohttp
from concurrent.futures import ProcessPoolExecutor

class AsyncYFinanceProvider:
    """Async version of YFinanceProvider using aiohttp."""

    async def get_fundamentals_async(self, session: aiohttp.ClientSession, ticker: str):
        """Fetch fundamentals asynchronously."""
        async with self.rate_limiter_async.acquire():
            async with session.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}") as resp:
                data = await resp.json()
                return self._parse_fundamentals(data)

    async def process_ticker_batch(self, session: aiohttp.ClientSession, tickers: List[str]):
        """Process multiple tickers concurrently."""
        tasks = [self.process_ticker_async(session, ticker) for ticker in tickers]
        return await asyncio.gather(*tasks, return_exceptions=True)

# Main execution
async def main():
    async with aiohttp.ClientSession() as session:
        provider = AsyncYFinanceProvider(max_requests_per_minute=58)

        # Process 50 tickers concurrently (limited by semaphore)
        results = await provider.process_ticker_batch(session, universe[:50])
```

**Rationale**:
- **Threading (current)**: Global Interpreter Lock (GIL) limits true parallelism
- **AsyncIO (proposed)**: Single-threaded event loop, no GIL contention
- Can handle 50+ concurrent HTTP requests efficiently
- Better I/O multiplexing (epoll/kqueue vs polling)
- Lower memory overhead (async tasks vs threads)

**Benefits**:
- 3-5x more concurrent requests with same memory
- Reduced context switching overhead
- Better CPU utilization
- Native support for timeouts and cancellation

**Challenges**:
- `yfinance` library is synchronous (need to use raw HTTP API)
- Significant code refactoring required
- Need to reimplement all yfinance data parsing
- Async code is harder to debug

**Implementation Plan**:
1. **Phase 1**: Create `AsyncYFinanceProvider` prototype
   - Implement fundamentals fetching via Yahoo Finance API
   - Add rate limiting with `asyncio.Semaphore`
   - Test with 100 tickers

2. **Phase 2**: Implement remaining data fetches
   - Analyst data
   - Volatility metrics
   - Options flow data

3. **Phase 3**: Migrate screener jobs
   - Update `run_daily_screeners.py` to use async
   - Add async Firestore operations
   - Comprehensive testing

4. **Phase 4**: Deployment
   - Deploy to staging environment
   - Run parallel with existing system
   - Monitor for errors
   - Switch over once validated

**Testing Plan**:
- Unit tests for all async methods
- Integration tests with real Yahoo Finance API
- Load testing with 1000+ tickers
- Compare results with current implementation (data accuracy)

**Risk**: High
- Major architectural change
- Potential for subtle async bugs (race conditions, deadlocks)
- Yahoo Finance API may have different rate limits than yfinance library
- Rollback requires keeping old code in place during transition

**Estimated Timeline**: 1-2 weeks
- Week 1: Implement AsyncYFinanceProvider
- Week 2: Migrate screener jobs and test

**Rollback**: Difficult - requires maintaining both implementations

---

### 7. Batch yfinance Requests (Alternative to AsyncIO)
**File**: `backend/jobs/run_daily_screeners.py`

**Proposed Change**:
```python
def process_ticker_batch(self, tickers: List[str], batch_size: int = 50):
    """
    Process tickers in batches using yfinance's multi-ticker download.

    yfinance can fetch multiple tickers in a single request, which is much
    faster than individual requests.
    """
    results = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]

        # Fetch all tickers in batch (single API call!)
        ticker_objects = yf.Tickers(' '.join(batch))

        # Process each ticker in the batch
        for ticker in batch:
            try:
                ticker_obj = ticker_objects.tickers[ticker]

                # All data already fetched - just parse it
                fundamentals = ticker_obj.info
                analyst_data = self._extract_analyst_data(ticker_obj)
                volatility = self._extract_volatility_data(ticker_obj)

                # Evaluate screeners
                result = self._evaluate_screeners(ticker, fundamentals, analyst_data, volatility)
                if result:
                    results.append(result)

            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")
                continue

    return results
```

**Rationale**:
- `yf.Tickers()` can fetch multiple tickers in parallel internally
- Reduces total API calls significantly
- Simpler than full AsyncIO migration
- Leverages yfinance's built-in batching

**Benefits**:
- Much simpler to implement than AsyncIO
- No need to reimplement yfinance parsing
- Still get significant performance improvement

**Challenges**:
- Batch size needs tuning (too large = memory issues, too small = no benefit)
- If one ticker in batch fails, need to handle gracefully
- Rate limiting becomes batch-level instead of request-level

**Testing Plan**:
1. Test with batch_size=10, 25, 50, 100
2. Measure memory usage for each batch size
3. Monitor for rate limit errors
4. Compare total execution time

**Risk**: Medium
- yfinance batch behavior may have quirks
- Need to ensure error handling for failed tickers
- Memory usage increases with batch size

**Estimated Timeline**: 2-3 days

**Rollback**: Easy - can revert to current per-ticker approach

---

## 📊 Expected Performance Summary

| Tier | Implementation Status | Expected Rate | Batch Runtime | Total Improvement | Effort |
|------|----------------------|---------------|---------------|-------------------|--------|
| **Baseline** | - | 2.16 tickers/min | 9.3 hours | 1x | - |
| **Tier 1** | ✅ Implemented | 2.4-2.6 tickers/min | 8.0 hours | 1.1-1.2x | 1 hour |
| **Tier 2** | 🔄 Recommended | 4-6 tickers/min | 4.0 hours | 2-3x | 3 hours |
| **Tier 3 (AsyncIO)** | 🚀 Future | 12-15 tickers/min | 1.5 hours | 6-7x | 2 weeks |
| **Tier 3 (Batching)** | 🚀 Alternative | 10-12 tickers/min | 1.8 hours | 5-6x | 3 days |

---

## 🔍 Monitoring and Metrics

### Key Metrics to Track

**Pre-Deployment**:
- Baseline ticker processing rate (tickers/min)
- API call rate (calls/min)
- Rate limit utilization (%)
- Average API calls per ticker

**Post-Deployment**:
- New ticker processing rate
- Improvement factor
- Rate limit error count
- Memory usage (Cloud Run)
- CPU utilization

### Logging Enhancements

Add to `run_daily_screeners.py`:
```python
def _log_detailed_metrics(self):
    """Log detailed performance metrics for analysis."""
    logger.info("=" * 80)
    logger.info("DETAILED PERFORMANCE METRICS")
    logger.info(f"  Worker Utilization: {self._calculate_worker_utilization():.1f}%")
    logger.info(f"  Token Bucket Fill Rate: {self._calculate_token_fill_rate():.1f}%")
    logger.info(f"  Average API Response Time: {self._calculate_avg_response_time():.2f}s")
    logger.info(f"  Lock Contention Events: {self._get_lock_contention_count()}")
    logger.info("=" * 80)
```

### A/B Testing

For Tier 2 and Tier 3 optimizations:
1. Deploy new version to separate Cloud Run Job
2. Run both versions side-by-side
3. Compare results for data accuracy
4. Compare performance metrics
5. Switch over if new version is validated

---

## 🛡️ Risk Management

### Rollback Strategy

**Tier 1**:
- Risk: Low
- Rollback: Git revert + redeploy (~5 minutes)

**Tier 2**:
- Risk: Medium
- Rollback: Git revert + redeploy (~5 minutes)
- Monitoring: Check logs for rate limit errors in first 30 minutes

**Tier 3**:
- Risk: High
- Rollback: Keep old version deployed, switch traffic back (~1 minute)
- Testing: Run parallel deployment for 1 week before full cutover

### Rate Limit Safety

**Current Safety Mechanisms**:
1. Token bucket at 58 req/min (97% of 60 limit)
2. Exponential backoff with jitter (4 retries)
3. 2x burst capacity (116 tokens)

**Additional Safety for Higher Tiers**:
- Circuit breaker pattern (if 5 consecutive rate limit errors, pause for 60s)
- Adaptive rate limiting (reduce rate if errors detected)
- Real-time monitoring dashboard

---

## 📝 Change Log

| Date | Version | Changes | Performance Impact |
|------|---------|---------|-------------------|
| 2025-11-16 | 1.0 | Initial baseline measurement | 2.16 tickers/min |
| 2025-11-16 | 1.1 | Tier 1 optimizations implemented | TBD (testing) |
| TBD | 1.2 | Tier 2 optimizations (planned) | Target: 12-15 tickers/min |
| TBD | 2.0 | Tier 3 optimizations (planned) | Target: 18-20 tickers/min |

---

## 🎯 Recommended Next Steps

1. **Immediate** (Today):
   - ✅ Deploy Tier 1 optimizations
   - Monitor Batch 4 run tomorrow evening
   - Collect performance metrics

2. **Short-term** (This Week):
   - If Tier 1 achieves 2.4-2.6 tickers/min: SUCCESS, proceed with Tier 2
   - If Tier 1 < 2.4 tickers/min: Investigate bottlenecks before proceeding
   - Document actual performance improvements

3. **Medium-term** (Next 2 Weeks):
   - If target not met with Tier 1+2: Evaluate Tier 3 options
   - Decision: AsyncIO (higher performance) vs Batching (easier implementation)
   - Create POC for chosen approach

4. **Long-term** (Next Month):
   - Full Tier 3 implementation and testing
   - Achieve target performance: 12-15 tickers/min (~1.5 hours per batch)
   - To go faster: Reduce API calls per ticker or upgrade to paid API tier

---

## 📚 References

- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [yfinance Library](https://github.com/ranaroussi/yfinance)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Cloud Run Concurrency Tuning](https://cloud.google.com/run/docs/configuring/concurrency)

---

**Document Maintained By**: Claude Code
**Last Updated**: November 16, 2025
**Next Review**: After Batch 4 run (November 17, 2025)
