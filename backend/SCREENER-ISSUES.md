# Stock Screener Performance & Code Quality Issues

**Created**: November 8, 2025
**Status**: Tracking low-priority improvements
**Related**: Phase 2 - Enhanced Screener Router

---

## Resolved Issues ✅

### HIGH Priority
- **Issue #3**: Limit Phase 1 results for technical analysis ✅ RESOLVED
  - **Problem**: Fetching technical data for 200+ stocks causes excessive API calls and slow response times
  - **Solution**: Added MAX_STOCKS_FOR_TECHNICAL = 100 limit with Lynch score sorting
  - **Impact**: Prevents fetching technical data for more than 100 stocks
  - **Location**: `backend/app/routers/screener.py:626-642`
  - **Commit**: Phase 2.1 Performance Improvements

### MEDIUM Priority
- **Issue #1**: Fix Gann reference price ✅ RESOLVED
  - **Problem**: Using `current_price` as both current AND reference price for Gann calculations doesn't give meaningful support/resistance levels
  - **Solution**: Changed to use 52-week low as reference price
  - **Code**: `reference_price = financials.get("52_week_low", current_price)`
  - **Impact**: More accurate Gann support/resistance levels based on recent price action
  - **Location**: `backend/app/routers/screener.py:726-730`
  - **Commit**: Phase 2.1 Performance Improvements

- **Issue #4**: Add rate limiting ✅ RESOLVED
  - **Problem**: No rate limiting on YFinance API calls could cause throttling errors
  - **Solution**: Added `@rate_limit` decorator with 100ms minimum interval between calls
  - **Impact**: Prevents API throttling during bulk screening operations
  - **Location**: `backend/app/services/yfinance_provider.py:20-50, 72, 151, 194`
  - **Commit**: Phase 2.1 Performance Improvements

### CRITICAL Priority (Performance)
- **Issue #7**: Sequential technical analysis causing 15-30 second response times ✅ RESOLVED
  - **Problem**: Phase 2 processed stocks sequentially with 2-3 API calls per stock
    - For 50 stocks: 100-150 sequential network requests
    - Rate limiting overhead: 100ms × 100 calls = 10+ seconds minimum
    - Network latency: 50-100ms per call = 5-10 seconds
    - **Total time: 15-30+ seconds for a single screen**
  - **Solution**: Implemented concurrent processing with controlled concurrency
    - Created `_process_single_stock_technical()` - Synchronous helper for one stock
    - Created `_process_technical_analysis_async()` - Async wrapper with semaphore
    - Created `_batch_process_technical_analysis()` - Batch coordinator with max_concurrent=5
    - Replaced sequential for loop with concurrent batch processing
  - **Impact**:
    - 70-80% reduction in response time (15-30 seconds → 3-6 seconds)
    - 5 concurrent workers for safe, respectful API usage
    - Maintains rate limiting protection per worker
  - **Location**: `backend/app/routers/screener.py:617-892, 1031-1044`
  - **Commit**: Phase 2.2 Concurrent Technical Analysis

---

## Pending Issues (LOW Priority)

### Issue #2: Optimize TechnicalIndicators Model Creation
**Priority**: Low
**Impact**: Minor performance improvement
**Effort**: Low (15 minutes)

**Problem**:
The `TechnicalIndicators` Pydantic model is created even when only pattern or Gann filtering is needed. Unnecessary object instantiation.

**Current Code** (`backend/app/routers/screener.py:662-668`):
```python
# Always created if apply_technical is True
tech_indicators = TechnicalIndicators(
    rsi_current=indicators["rsi"]["current"],
    rsi_oversold=indicators["rsi"]["oversold"],
    rsi_overbought=indicators["rsi"]["overbought"],
    macd_bullish_crossover=indicators["macd"]["bullish_crossover"],
    macd_bearish_crossover=indicators["macd"]["bearish_crossover"],
)
```

**Recommended Fix**:
```python
# Only create if RSI or MACD filters are active
tech_indicators = None
if (request.technical_filters.rsi_condition != RSICondition.ANY or
    request.technical_filters.macd_condition != MACDCondition.ANY):
    tech_indicators = TechnicalIndicators(
        rsi_current=indicators["rsi"]["current"],
        rsi_oversold=indicators["rsi"]["oversold"],
        rsi_overbought=indicators["rsi"]["overbought"],
        macd_bullish_crossover=indicators["macd"]["bullish_crossover"],
        macd_bearish_crossover=indicators["macd"]["bearish_crossover"],
    )
```

**Benefits**:
- Slightly faster execution when only pattern/Gann filters are used
- Cleaner code with intentional model creation

---

### Issue #5: Improve Exception Handling
**Priority**: Low
**Impact**: Better error visibility during development
**Effort**: Low (20 minutes)

**Problem**:
Broad `except Exception` catches everything, including important errors that should be surfaced to developers.

**Current Code** (`backend/app/routers/screener.py:708`):
```python
except Exception as e:
    logger.debug(f"Technical analysis failed for {ticker}: {e}")
    continue
```

**Recommended Fix**:
```python
import os

except (ValueError, KeyError, ConnectionError, pd.errors.EmptyDataError) as e:
    # Expected errors - log at debug level
    logger.debug(f"Technical analysis failed for {ticker}: {e}")
    continue
except Exception as e:
    # Unexpected errors - log at error level
    logger.error(f"Unexpected error in technical analysis for {ticker}: {e}", exc_info=True)
    # Re-raise in development for debugging
    if os.getenv("ENV") == "development":
        raise
    continue
```

**Benefits**:
- Developers see unexpected errors immediately
- Production gracefully handles expected errors
- Better debugging with stack traces in development

**Additional Locations to Update**:
- Line 620: Phase 1 fundamental filtering
- Line 752: Main result processing
- Line 717: Ticker details fetching

---

### Issue #6: Move Ticker Details Fetch Earlier
**Priority**: Low
**Impact**: Minor performance improvement
**Effort**: Low (10 minutes)

**Problem**:
Ticker details (company name, sector) are fetched AFTER technical analysis. If technical analysis fails, the API call was wasted.

**Current Code** (`backend/app/routers/screener.py:712-719`):
```python
# Technical analysis happens first (lines 666-710)
...

# Then ticker details (wasteful if technical analysis failed)
try:
    details = market_data.get_ticker_details(ticker)
    company_name = details.get("name", ticker)
    sector = details.get("sector", "")
except Exception:
    company_name = ticker
    sector = ""
```

**Recommended Fix**:
Move ticker details fetch to BEFORE technical analysis block (before line 665):
```python
# Get ticker details FIRST (cheaper than technical analysis)
try:
    details = market_data.get_ticker_details(ticker)
    company_name = details.get("name", ticker)
    sector = details.get("sector", "")
except Exception:
    company_name = ticker
    sector = ""

# THEN do expensive technical analysis
if apply_technical:
    try:
        # Get technical indicators
        ...
```

**Benefits**:
- Avoids wasted API call if technical analysis filters out the stock
- Logical ordering: cheap operations first, expensive operations later

---

## Future Enhancements (Not Issues)

### Response Streaming with Server-Sent Events (SSE)
**Priority**: Future Enhancement
**Effort**: Medium (2-3 hours)

**Idea**: Stream results to frontend as they're found instead of waiting for all processing to complete.

**Benefits**:
- Users see results immediately (progressive enhancement)
- Better perceived performance
- Can cancel long-running screens

**Implementation**:
```python
from fastapi.responses import StreamingResponse

async def stream_screening_results(request):
    async def result_generator():
        for ticker, financials in fundamental_passed:
            result = await process_stock(ticker, financials)
            if result:
                yield f"data: {result.model_dump_json()}\n\n"

    return StreamingResponse(result_generator(), media_type="text/event-stream")
```

**Trade-offs**:
- More complex frontend code to handle streaming
- Need to update API contract
- Harder to implement pagination with streaming

---

## How to Use This File

1. **When working on performance**: Check this file for easy wins
2. **Before major releases**: Consider addressing pending issues
3. **When debugging**: Reference the resolved issues section for context
4. **Adding new issues**: Use the same format (Problem → Fix → Benefits)

---

## Related Files

- `backend/app/routers/screener.py` - Main screener endpoint
- `backend/app/services/yfinance_provider.py` - YFinance data provider
- `backend/app/financial_models/gann.py` - Gann calculator
- `backend/app/financial_models/patterns.py` - Pattern detector
- `SCREENER-EVOLUTION.md` - Main implementation tracking

---

**Last Updated**: November 8, 2025
**Maintainer**: Development Team
