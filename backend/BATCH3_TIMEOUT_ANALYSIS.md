# Batch 3 Timeout Analysis & Optimization Impact

**Report Date**: November 16, 2025
**Event**: Batch 3 (K-N) timeout after 3 hours
**Context**: Job started at 11:00 AM EST (16:00 UTC), before Tier 1 optimizations deployed

---

## Executive Summary

**Will recent optimizations fix the timeout?**
**SHORT ANSWER**: Tier 1 optimizations alone are **UNLIKELY** to prevent future timeouts. Tier 2 optimizations (worker tuning) will be needed to achieve target performance.

**KEY FINDINGS**:
- Batch 3 processed **885/1,200 stocks** (73.75%) before timeout
- Performance: **4.9 tickers/min** (vs target of **13-14 tickers/min**)
- **Gap**: Need **2.7x improvement** to meet target
- **Tier 1 optimizations**: Expected **1.1-1.2x improvement** (10-20%)
- **Delisted ticker exclusions**: Will save ~9 tickers = **0.75% improvement**

**RECOMMENDATION**:
1. ✅ Monitor next batch run with Tier 1 optimizations
2. ⚠️ Prepare to implement Tier 2 optimizations (increase workers to 10)
3. ✅ Delisted ticker exclusions added (marginal improvement)

---

## Batch 3 Performance Breakdown

### Metrics
| Metric | Value |
|--------|-------|
| **Total Target** | ~1,200 stocks (K-N range) |
| **Processed** | 885 stocks (73.75%) |
| **Runtime** | 3 hours (10,800 seconds) |
| **Timeout Limit** | 3 hours (10,800 seconds) |
| **Processing Rate** | 4.92 tickers/min |
| **Stocks/Hour** | ~295 stocks/hour |
| **Average Time/Stock** | ~12.2 seconds |

### Performance Gap
| Category | Value | Status |
|----------|-------|--------|
| **Current Performance** | 4.92 tickers/min | ❌ 65% below target |
| **Target Performance** | 13-14 tickers/min | 🎯 Goal |
| **Required Improvement** | 2.65x - 2.85x | ⚠️ Significant |

---

## Recent Optimizations (Tier 1)

### Deployed: November 16, 2025 (after Batch 3 run)

**Status**: ✅ Implemented
**Expected Impact**: 1.1-1.2x improvement (10-20%)

### Changes Made

#### 1. Reduced Token Bucket Sleep Interval
**File**: `rate_limiter.py:132`
```python
# Before: 100ms sleep (slow token acquisition)
time.sleep(min(sleep_time, 0.1))

# After: 10ms sleep (10x faster)
time.sleep(min(sleep_time, 0.01))
```
**Impact**: Workers acquire tokens 10x faster, reducing idle time

---

#### 2. Increased Burst Capacity
**File**: `yfinance_provider.py:71`
```python
# Before: 55 tokens capacity
capacity=max_requests_per_minute  # 1x rate

# After: 116 tokens capacity
capacity=max_requests_per_minute * 2  # 2x burst
```
**Impact**: Better token banking during idle periods, reduces blocking

---

#### 3. Increased Rate Limit
**File**: `run_daily_screeners.py:86`
```python
# Before: 55 req/min (91.7% utilization)
YFinanceProvider(max_requests_per_minute=55)

# After: 58 req/min (96.7% utilization)
YFinanceProvider(max_requests_per_minute=58)
```
**Impact**: 5.5% more API calls per minute (55 → 58)

---

#### 4. Delisted Ticker Exclusions (NEW - this PR)
**Files**:
- `ticker_universe.py` - Permanent exclusion list
- `add_batch3_additional_delisted.py` - Firestore blacklist script

**Tickers Added** (9 total):
- `MSTKY`, `MASTLW`, `MTMTY`, `MSSWF`, `MSTLW`
- `MTEKW`, `MTLPF`, `MUNX`, `MVSTW`

**Impact Calculation**:
- 9 tickers excluded
- Each ticker = ~3 API calls (fundamentals, analyst, volatility)
- Saves: **27 API calls** per batch run
- At current rate (4.9 tickers/min): **~5.5 minutes saved**
- **Improvement**: ~0.5% (marginal but helps)

---

## Performance Projections

### Scenario Analysis

| Scenario | Tickers/Min | Batch Runtime | Status |
|----------|-------------|---------------|--------|
| **Baseline (Batch 3)** | 4.9 | 4.1 hours | ❌ Timeout |
| **Tier 1 (10% improvement)** | 5.4 | 3.7 hours | ❌ Still timeout |
| **Tier 1 (20% improvement)** | 5.9 | 3.4 hours | ❌ Still timeout |
| **Tier 2 (2.5x improvement)** | 12.3 | 1.6 hours | ✅ Success |
| **Tier 3 (3x improvement)** | 14.7 | 1.4 hours | ✅ Success |
| **Target** | 13-14 | 1.4-1.5 hours | 🎯 Goal |

### Key Insights

1. **Tier 1 alone is insufficient**: Even with 20% improvement, batch runtime would be 3.4 hours (still exceeds 3-hour timeout)

2. **Need 2.5x improvement minimum**: To complete 1,200 stocks in 3 hours requires ~6.7 tickers/min (2.5x from Tier 1 optimizations)

3. **Tier 2 required**: Increasing workers from 6 to 10 expected to provide 2-3x improvement, which would meet target

---

## Why Was Batch 3 So Slow?

### Contributing Factors

#### 1. **Pre-Tier 1 Optimizations**
The batch ran at 11:00 AM EST, **BEFORE** the following optimizations were deployed:
- Slow token acquisition (100ms sleep)
- Lower burst capacity (1x vs 2x)
- Conservative rate limit (55 vs 58 req/min)

#### 2. **Delisted Tickers**
Encountered multiple delisted tickers that caused:
- Timeout errors (30 second default timeout per ticker)
- 404 errors (wasted API calls)
- Retry attempts with exponential backoff

**Known delisted tickers in K-N range**:
- Previous batch 3 run: 9 tickers (MMTX, MNZLY, MOVAA, MPJS, MRCA, MREGY, MROSY, MRUWY, LOMWF)
- This batch 3 run: 9 additional tickers (now added to exclusion list)
- Batch 2: 1 ticker (JMAKY, also excluded)
- **Total**: 19 delisted tickers = ~57 wasted API calls = ~12 minutes lost

#### 3. **Lock Contention**
With 6 workers competing for tokens:
- Each API call requires lock acquisition
- 3 API calls per ticker = 3 lock acquisitions
- With 100ms sleep, workers spend significant time waiting

#### 4. **GIL (Global Interpreter Lock)**
Python's GIL limits true parallelism:
- 6 threads = only 1 active at a time for CPU-bound work
- Context switching overhead
- AsyncIO (Tier 3) would eliminate this bottleneck

---

## Optimization Roadmap

### ✅ Tier 1: Rate Limit Tuning (COMPLETE)
- **Status**: Deployed November 16, 2025
- **Impact**: 1.1-1.2x (10-20% improvement)
- **Next Batch Runtime (estimated)**: 3.4-3.7 hours
- **Verdict**: Still exceeds 3-hour timeout ❌

### 🔄 Tier 2: Worker Tuning (RECOMMENDED NEXT)
- **Status**: Not implemented
- **Change**: Increase workers from 6 → 10
- **Impact**: 2-3x improvement (estimated 12-15 tickers/min)
- **Next Batch Runtime (estimated)**: 1.3-1.7 hours
- **Verdict**: Meets target ✅
- **Risk**: Medium (need to monitor memory usage)
- **Implementation**: 30 minutes

### 🚀 Tier 3: AsyncIO Migration (FUTURE)
- **Status**: Not implemented
- **Impact**: 6-7x improvement (18-20+ tickers/min)
- **Next Batch Runtime (estimated)**: <1 hour
- **Risk**: High (major refactor)
- **Implementation**: 1-2 weeks

---

## Delisted Ticker Impact

### Tickers Added to Exclusion List

**Permanent Exclusion** (`ticker_universe.py`):
```python
def _get_delisted_ticker_list(self) -> Set[str]:
    return {
        # Batch 3 - November 16, 2025 timeout run
        "MSTKY", "MASTLW", "MTMTY", "MSSWF", "MSTLW",
        "MTEKW", "MTLPF", "MUNX", "MVSTW",

        # Batch 3 - Previous runs
        "MMTX", "MNZLY", "MOVAA", "MPJS", "MRCA",
        "MREGY", "MROSY", "MRUWY", "LOMWF",
    }
```

**Firestore Blacklist** (30-day TTL):
- Script: `add_batch3_additional_delisted.py`
- Runtime cache: Skips known delisted tickers automatically

### Impact Calculation

| Metric | Value |
|--------|-------|
| Delisted tickers excluded | 9 (new) + 9 (previous) + 1 (Batch 2: JMAKY) = 19 total |
| API calls saved per ticker | ~3 (fundamentals, analyst, volatility) |
| Total API calls saved | 57 calls |
| Time saved (at 58 req/min) | ~59 seconds |
| Time saved (including timeouts) | ~5-10 minutes |
| % Improvement | ~0.5-1% (marginal) |

---

## Recommendations

### Immediate Actions (Next Batch Run)

1. ✅ **Deploy Tier 1 Optimizations** (COMPLETE)
   - Already deployed on November 16, 2025
   - Will be active for next batch run

2. ✅ **Add Delisted Ticker Exclusions** (THIS PR)
   - Permanent exclusion in `ticker_universe.py`
   - Firestore blacklist via script
   - Saves ~5-10 minutes per batch

3. 📊 **Monitor Next Batch Run** (Batch 4 or Batch 5)
   - Track processing rate (should be ~5.4-5.9 tickers/min)
   - Monitor for timeouts
   - Check API rate limit utilization
   - If still times out → proceed to Tier 2

### Short-Term Actions (If Batch Still Times Out)

4. ⚠️ **Implement Tier 2 Optimizations**
   - Increase workers from 6 → 10
   - **Expected Impact**: 2-3x improvement → ~1.5 hours per batch
   - **Risk**: Medium (monitor Cloud Run memory)
   - **Implementation**: 30 minutes

### Long-Term Actions (Optional)

5. 🚀 **Consider Tier 3 (AsyncIO)** - Only if needed
   - **Benefits**: 6-7x improvement, <1 hour per batch
   - **Cost**: 1-2 weeks development + testing
   - **Decision Point**: Only if Tier 2 insufficient

---

## Testing Plan

### Next Batch Run Validation

**Batch to Monitor**: Batch 4 (O-S) or Batch 5 (T-Z)
**Expected Start Time**: November 17-18, 2025

**Metrics to Track**:
1. Processing rate (tickers/min)
2. Total runtime (should be <3 hours)
3. API rate limit utilization (target: 95%+)
4. Delisted ticker skips (should see log entries)
5. Memory usage (Cloud Run metrics)

**Success Criteria**:
- ✅ Completes all ~1,200 stocks
- ✅ Runtime < 2.5 hours (buffer for variability)
- ✅ No rate limit errors
- ✅ Memory usage < 2GB

**Failure Criteria** (triggers Tier 2):
- ❌ Timeout at 3 hours
- ❌ Processes <1,000 stocks
- ❌ Processing rate <7 tickers/min

---

## Conclusion

### Answer to Original Question: "Do we think our other optimizations will address this slow processing?"

**TIER 1 ALONE: NO** ❌
- Batch 3 ran at 4.9 tickers/min (before Tier 1)
- Tier 1 provides 10-20% improvement → 5.4-5.9 tickers/min
- Still need 13-14 tickers/min to complete in 1.5 hours
- At 5.9 tickers/min, batch would take 3.4 hours (still timeout)

**TIER 1 + TIER 2: YES** ✅
- Increasing workers to 10 should provide 2-3x improvement
- Combined with Tier 1: ~12-15 tickers/min
- Estimated runtime: 1.3-1.7 hours (well under 3-hour limit)

**RECOMMENDED PATH**:
1. ✅ Deploy Tier 1 (done) + delisted exclusions (this PR)
2. 📊 Monitor next batch run
3. ⚠️ If still times out → implement Tier 2 (increase workers)
4. 🚀 Tier 3 (AsyncIO) only if absolutely necessary

### Delisted Ticker Exclusions

**Impact**: Marginal (~0.5-1% improvement, ~5-10 minutes saved)
**Value**: Worth doing because:
- Prevents wasted API calls on invalid tickers
- Reduces error noise in logs
- Low implementation effort (already done in this PR)
- Compounds with other optimizations

---

## Files Modified (This PR)

1. **`backend/app/services/ticker_universe.py`**
   - Added `_get_delisted_ticker_list()` method
   - Added 18 Batch 3 delisted tickers (plus JMAKY from Batch 2) to permanent exclusion list
   - Updated `_apply_basic_filters()` to check delisted list

2. **`backend/jobs/add_batch3_additional_delisted.py`** (NEW)
   - Script to add 9 new delisted tickers to Firestore blacklist
   - Preserves failure counts for existing entries
   - Includes statistics reporting

---

**Next Steps**: Monitor Batch 4/5 run and assess if Tier 2 optimizations are needed.
