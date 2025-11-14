# Future Improvements & Technical Debt

This document tracks issues identified during code review that should be addressed in future PRs.

---

## Priority: Important (Should Fix Soon)

### 1. Input Validation for TokenBucket
**Issue**: TokenBucket doesn't validate initialization parameters
- `rate = 0` would cause division by zero
- `capacity = 0` would make bucket unusable
- Negative values would cause undefined behavior

**Suggested Fix** (in `TokenBucket.__init__`, line 39):
```python
if rate <= 0:
    raise ValueError("rate must be positive")
if capacity <= 0:
    raise ValueError("capacity must be positive")
if time_unit <= 0:
    raise ValueError("time_unit must be positive")
```

**Impact**: Low (unlikely to be triggered in production)  
**Effort**: Trivial  
**Estimated Time**: 5 minutes

---

### 2. Input Validation for TokenBucket.acquire()
**Issue**: `acquire()` doesn't validate the `tokens` parameter
- Negative tokens would increase the count instead of decreasing
- `tokens > capacity` would wait forever (impossible to fulfill)

**Suggested Fix** (in `TokenBucket.acquire()`, line 73):
```python
if tokens <= 0:
    raise ValueError("tokens must be positive")
if tokens > self.capacity:
    raise ValueError(f"Cannot acquire {tokens} tokens (capacity is {self.capacity})")
```

**Impact**: Low (unlikely to be triggered)  
**Effort**: Trivial  
**Estimated Time**: 5 minutes

---

### 3. Token Efficiency with Cached Data (Code Review Feedback)
**Issue**: `get_comprehensive_data()` acquires tokens upfront even when data is cached

**Current Behavior** (line 1440):
```python
# Acquire all tokens upfront
if tokens_needed > 0:
    self._acquire_rate_limit(tokens=tokens_needed)

# Later... if data is cached, methods return without using tokens
if cached_data is not None:
    return cached_data  # Token was acquired but not used
```

**Trade-off Analysis**:
- ❌ Wastes tokens when data is cached (token acquired but not used)
- ✅ Simpler code logic (acquire once vs. check cache, then acquire conditionally)
- ✅ Prevents deadlock scenarios in concurrent environments
- ✅ More predictable rate limiting behavior

**Potential Fix** (if cache hit rates are high >50%):
- Check caches before acquiring tokens
- Calculate exact tokens needed based on cache misses
- Acquire only necessary tokens
- Note: Adds complexity and potential for race conditions

**Impact**: Low (acceptable trade-off unless cache hit rates are consistently high)
**Effort**: Moderate (requires careful thread-safe cache checking before token acquisition)
**Estimated Time**: 2-3 hours
**Recommendation**: Monitor cache hit rates in production; only optimize if >50% hit rate

---

## Priority: Nice to Have (Technical Debt)

### 4. Test Code Duplication
**Issue**: Test files duplicate implementation instead of importing production code

**Files Affected**:
- `backend/test_yfinance_unit.py` - Duplicates `TokenBucket` class (3 times!)
- Same file - Duplicates cache implementation

**Current Problem**:
```python
# test_yfinance_unit.py lines 28-70
class TokenBucket:  # Duplicate of production class
    def __init__(...): ...
    # Entire implementation duplicated
```

**Suggested Fix**:
```python
from app.services.yfinance_provider import TokenBucket  # Import real class

def test_token_bucket():
    """Test using production implementation."""
    bucket = TokenBucket(rate=100, capacity=20)
    # Test actual production code
```

**Impact**: Medium (tests don't verify production code)  
**Effort**: Moderate (need to refactor all test duplications)  
**Estimated Time**: 1-2 hours

---

### 5. TokenBucket Race Condition (Nitpick)
**Issue**: Sleep happens outside lock, creating potential for suboptimal wait times

**Current Pattern** (line 115):
```python
with self.lock:
    # Calculate sleep_time
    sleep_time = tokens_needed / self.tokens_per_second

# Sleep outside lock (another thread could consume tokens here)
time.sleep(min(sleep_time, 0.1))
```

**Why This Happens**:
- Can't hold lock during sleep (would block all threads)
- Between releasing lock and sleeping, another thread could consume tokens
- Thread might sleep longer than necessary

**Suggested Fix** (advanced):
- Use `threading.Condition` instead of raw lock
- Allow threads to wait on condition and be notified when tokens available
- More complex but more precise

**Impact**: Very Low (theoretical issue, unlikely to cause problems)  
**Effort**: High (requires refactoring TokenBucket)  
**Estimated Time**: 3-4 hours  
**Recommendation**: Document as known trade-off, don't fix

---

## Summary

### Fix Immediately (before next deployment):
- ✅ Double rate limiting - **FIXED**
- ✅ Thread safety - **FIXED**
- ✅ Cache key inconsistency - **FIXED**
- ✅ Options flow token waste - **FIXED**
- ✅ Unused import - **FIXED**

### Fix Soon (next PR):
1. ⏳ Input validation for TokenBucket (10 minutes total)
2. ⏳ Token efficiency with cached data (2-3 hours, only if cache hit rate >50%)

### Fix Later (technical debt):
3. ⏳ Test code duplication (1-2 hours)
4. ⏳ TokenBucket race condition (document only, don't fix)

---

**Total Estimated Effort for "Fix Soon"**: ~10 minutes (validation) + 2-3 hours (token efficiency, if needed) = 2.5-3.5 hours
**Total Estimated Effort for "Fix Later"**: 1-2 hours (tests)

---

**Document Created**: 2025-11-14  
**Created By**: Claude Code (Anthropic)
