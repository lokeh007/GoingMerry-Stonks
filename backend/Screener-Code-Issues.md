# Screener Code Issues & Improvements

**Last Updated**: 2025-11-08
**Status**: Post-yfinance migration code review
**Code Version**: v3.1.2-relaxed-presets

---

## 🔴 CRITICAL Priority

### Issue #1: Partial Polygon Migration - MarketDataProvider Still Used
**Location**: `app/routers/screener.py:33, 205, 208, 730, 927, 936`

**Problem**: Despite migrating to yfinance for fundamentals, the code still imports and uses `MarketDataProvider` (Polygon wrapper) for:
- Stock universe fetching (line 208, 936)
- Company name/sector lookup (lines 730-735)

**Impact**:
- Creates unnecessary Polygon API dependency
- May hit Polygon rate limits (5 calls/min)
- Inconsistent data sources (yfinance fundamentals + Polygon details)

**Code Examples**:
```python
# Line 205-208 (Lynch Fast Growers endpoint)
market_data = MarketDataProvider()  # ❌ Still using Polygon
tickers = market_data.get_stock_universe(universe)  # ❌ Polygon API call

# Line 730-735 (Advanced screener)
try:
    details = market_data.get_ticker_details(ticker)  # ❌ Polygon API call
    company_name = details.get("name", ticker)
    sector = details.get("sector", "")
except Exception:
    company_name = ticker
    sector = ""
```

**Recommended Fix**:
```python
# Solution: Use yfinance data already fetched in Phase 1
company_name = financials.get("company_name", ticker)  # ✅ From yfinance
sector = financials.get("sector", "")  # ✅ From yfinance

# Remove MarketDataProvider import entirely
# Move get_stock_universe() to YFinanceProvider or create standalone function
```

**Priority**: CRITICAL - This defeats the purpose of migrating to yfinance

---

### Issue #2: Missing yfinance Fields Referenced Throughout Code
**Location**: `app/routers/screener.py:259, 261, 755, 756, 758`

**Problem**: Code references fields that `yfinance_provider.get_fundamentals()` doesn't return:
- `pe_ratio` (lines 259, 756)
- `revenue_growth` (lines 261, 758)

**Impact**:
- StockScreenerResult objects have `None` for these fields
- Frontend may expect these values
- Breaks data contract with API consumers

**Code Examples**:
```python
# Line 259, 261
result = StockScreenerResult(
    pe_ratio=financials.get("pe_ratio"),  # ❌ Always None
    revenue_growth=financials.get("revenue_growth"),  # ❌ Always None
)
```

**Current yfinance_provider.get_fundamentals() Returns**:
```python
{
    "ticker": str,
    "company_name": str,
    "sector": str,
    "market_cap": float,
    "peg_ratio": float,
    "eps_growth": float,
    "debt_to_equity": float,
    "roe": float,
    "institutional_ownership": float,
    "current_ratio": float,
    "current_price": float,
    "timestamp": str,
}
```

**Recommended Fix**:
```python
# Option 1: Calculate PE ratio from available data
# PE = Price / EPS
# Add to yfinance_provider.get_fundamentals():
info = stock.info
eps = info.get("trailingEps")
current_price = info.get("currentPrice") or info.get("regularMarketPrice")
pe_ratio = (current_price / eps) if eps and eps > 0 else None

fundamentals["pe_ratio"] = pe_ratio

# Option 2: Fetch revenue growth from quarterly financials
# Add to yfinance_provider.get_fundamentals():
revenue_growth = self._calculate_revenue_growth(stock)
fundamentals["revenue_growth"] = revenue_growth
```

**Priority**: CRITICAL - Missing data affects all screener results

---

### Issue #3: Inconsistent Price Field Naming
**Location**: `app/routers/screener.py:258, 702, 755`

**Problem**: Code uses both `price` and `current_price` interchangeably:
- Line 258: Correctly uses `financials.get("current_price")`
- Line 702: Incorrectly uses `financials.get("price", 0)`
- Line 755: Incorrectly uses `financials.get("price")`

**Impact**:
- Gann level calculation gets 0 for current_price (line 702)
- Advanced screener results have None for price (line 755)
- Inconsistent data in API responses

**Code Examples**:
```python
# Line 702 (Gann level detection)
current_price = financials.get("price", 0)  # ❌ Should be "current_price"

# Line 755 (Advanced screener result)
result = StockScreenerResult(
    price=financials.get("price"),  # ❌ Should be "current_price"
)
```

**Recommended Fix**:
```python
# Replace ALL instances of financials.get("price") with:
current_price = financials.get("current_price")
```

**Priority**: CRITICAL - Breaks Gann analysis and price display

---

### Issue #4: Missing 52-Week Low for Gann Calculations
**Location**: `app/routers/screener.py:705`

**Problem**: Gann level calculation uses `52_week_low` which isn't in yfinance fundamentals:
```python
reference_price = financials.get("52_week_low", current_price)  # ❌ Always falls back to current_price
```

**Impact**:
- Gann levels use current_price as reference instead of proper 52-week low
- Support/resistance calculations are inaccurate
- Gann location filter (AT_SUPPORT, AT_RESISTANCE) may not work correctly

**Recommended Fix**:
```python
# Option 1: Add 52-week low to yfinance_provider.get_fundamentals()
info = stock.info
fundamentals["week_52_low"] = info.get("fiftyTwoWeekLow")
fundamentals["week_52_high"] = info.get("fiftyTwoWeekHigh")

# Option 2: Fetch historical data to calculate 52-week low
hist = stock.history(period="1y")
fundamentals["week_52_low"] = hist["Low"].min()
fundamentals["week_52_high"] = hist["High"].max()
```

**Priority**: CRITICAL - Breaks Gann technical analysis

---

### Issue #5: max_earnings_growth Filter Breaks When None
**Location**: `app/routers/screener.py:234, 1089`

**Problem**: When `max_earnings_growth` is `None` (no upper limit), comparison fails:
```python
# Line 234 (Lynch Fast Growers)
passes_screen = (
    min_earnings_growth <= eps_growth <= max_earnings_growth  # ❌ Fails if max is None
)

# Line 1089 (Advanced screener)
if filters.max_eps_growth is not None and eps_growth > filters.max_eps_growth:
    return False  # ✅ Correctly handles None
```

**Impact**:
- Lynch Fast Growers endpoint crashes with TypeError when max_earnings_growth is None
- Presets with `max_eps_growth: None` don't work

**Code Examples**:
```python
# Current broken code (line 234):
passes_screen = (
    min_earnings_growth <= eps_growth <= max_earnings_growth  # TypeError if None
    and peg_ratio < max_peg_ratio
    and debt_to_equity < max_debt_to_equity
    and current_ratio >= min_current_ratio
    and market_cap >= min_market_cap
)
```

**Recommended Fix**:
```python
# Fix: Add None check
eps_growth_passes = min_earnings_growth <= eps_growth
if max_earnings_growth is not None:
    eps_growth_passes = eps_growth_passes and eps_growth <= max_earnings_growth

passes_screen = (
    eps_growth_passes
    and peg_ratio < max_peg_ratio
    and debt_to_equity < max_debt_to_equity
    and current_ratio >= min_current_ratio
    and market_cap >= min_market_cap
)
```

**Priority**: CRITICAL - Causes endpoint crashes

---

## 🟠 HIGH Priority

### Issue #6: Outdated Documentation in /screeners List
**Location**: `app/routers/screener.py:327-341`

**Problem**: The `/screeners` endpoint shows outdated criteria that don't match actual presets:
```python
"criteria": [
    "Earnings growth: 10-25% annually",  # ❌ Actual: 15% min, no max
    "PEG ratio < 2.5",  # ❌ Actual Fast Growers: 2.0
    "Current ratio > 1.0",  # ✅ Correct
    "Debt-to-equity < 2.0",  # ❌ Actual: 0.8
],
```

**Impact**:
- Users get misleading information about screening criteria
- Documentation doesn't reflect recent preset relaxations
- Trust issues when results don't match documented criteria

**Recommended Fix**:
```python
# Update to match actual Fast Growers preset (lines 401-408)
"criteria": [
    "Earnings growth: 15%+ annually (no upper limit)",
    "PEG ratio < 2.0",
    "Current ratio ≥ 1.0",
    "Debt-to-equity < 0.8",
    "ROE ≥ 15%",
    "Market cap ≥ $1B",
],
```

**Priority**: HIGH - Misleading user-facing documentation

---

### Issue #7: Incorrect Exception Handling (MarketDataError)
**Location**: `app/routers/screener.py:272-275`

**Problem**: Code catches `MarketDataError` (Polygon exception) but yfinance raises different exceptions:
```python
except MarketDataError as e:  # ❌ yfinance doesn't raise this
    logger.warning(f"Failed to fetch data for {ticker}: {e}")
    failed_tickers.append(ticker)
    continue
```

**Impact**:
- Actual yfinance exceptions (YFinanceError, requests.exceptions, etc.) won't be caught
- Error handling is ineffective
- May cause unhandled exceptions to propagate

**Recommended Fix**:
```python
# Catch generic exceptions or create yfinance-specific exception hierarchy
except Exception as e:
    logger.warning(f"Failed to fetch data for {ticker}: {e}")
    failed_tickers.append(ticker)
    continue
```

**Priority**: HIGH - Incorrect error handling

---

### Issue #8: get_stock_universe() Existence Unclear
**Location**: `app/routers/screener.py:934`

**Problem**: Code calls `yf_provider.get_stock_universe(request.universe.upper())` but this method may not exist:
```python
if request.universe in ["nasdaq", "nyse", "all"]:
    tickers = yf_provider.get_stock_universe(request.universe.upper())  # ❌ Does this method exist?
else:
    tickers = market_data.get_stock_universe(request.universe)  # ❌ Still uses Polygon
```

**Impact**:
- May cause AttributeError if method doesn't exist
- Inconsistent behavior between universe types
- Still relies on Polygon for some universes

**Recommended Fix**:
```python
# Verify YFinanceProvider has get_stock_universe() method
# If not, implement it or use MarketDataProvider.get_stock_universe() for all universes
# But move the stock list logic away from Polygon dependency

# Ideal: Create a standalone stock_universes.py module
from ..data.stock_universes import get_stock_universe

tickers = get_stock_universe(request.universe)
```

**Priority**: HIGH - Potential runtime error

---

### Issue #9: Duplicate Company Name Fetching Logic
**Location**: `app/routers/screener.py:242-244, 729-735`

**Problem**: Lynch Fast Growers correctly uses yfinance data (lines 242-244), but advanced screener still uses Polygon (729-735):

**Lynch Fast Growers (Correct)**:
```python
# Line 242-244
company_name = financials.get("company_name", ticker)  # ✅ From yfinance
sector = financials.get("sector", "")  # ✅ From yfinance
```

**Advanced Screener (Incorrect)**:
```python
# Line 729-735
try:
    details = market_data.get_ticker_details(ticker)  # ❌ Polygon API call
    company_name = details.get("name", ticker)
    sector = details.get("sector", "")
except Exception:
    company_name = ticker
    sector = ""
```

**Impact**:
- Inconsistent data sources between endpoints
- Unnecessary Polygon API calls in advanced screener
- Duplicate logic across endpoints

**Recommended Fix**:
```python
# Replace lines 729-735 with:
company_name = financials.get("company_name", ticker)
sector = financials.get("sector", "")
```

**Priority**: HIGH - Duplicate code and unnecessary Polygon dependency

---

## 🟡 MEDIUM Priority

### Issue #10: Hardcoded Technical Analysis Stock Limit
**Location**: `app/routers/screener.py:973`

**Problem**: MAX_STOCKS_FOR_TECHNICAL hardcoded to 100 with no configuration option:
```python
MAX_STOCKS_FOR_TECHNICAL = 100
```

**Impact**:
- Users can't adjust this limit based on their use case
- May be too restrictive for some scenarios
- May be too permissive for API rate limits

**Recommended Fix**:
```python
# Option 1: Make it configurable via environment variable
import os
MAX_STOCKS_FOR_TECHNICAL = int(os.getenv("MAX_STOCKS_FOR_TECHNICAL", "100"))

# Option 2: Add as request parameter
class AdvancedScreenerRequest(BaseModel):
    ...
    max_stocks_for_technical: int = Field(100, ge=10, le=500)
```

**Priority**: MEDIUM - Inflexible configuration

---

### Issue #11: Minimal Field Mapping in _CRITERIA_KEY_MAP
**Location**: `app/routers/screener.py:45-48`

**Problem**: Module-level constant only has 2 mappings and has a comment claiming performance benefits:
```python
_CRITERIA_KEY_MAP = {
    "min_eps_growth": "min_earnings_growth",
    "max_eps_growth": "max_earnings_growth",
}
```

**Impact**:
- Over-engineering for 2 simple mappings
- Comment claims "identity mappings removed for performance" but dict lookup is same speed
- Harder to maintain than inline renaming

**Recommended Fix**:
```python
# Option 1: Remove constant and do inline renaming
criteria = {
    "min_earnings_growth": raw_criteria["min_eps_growth"],
    "max_earnings_growth": raw_criteria["max_eps_growth"],
    **{k: v for k, v in raw_criteria.items() if k not in ["min_eps_growth", "max_eps_growth"]}
}

# Option 2: Just use raw_criteria directly and fix _generate_screening_reasons()
```

**Priority**: MEDIUM - Code clarity

---

### Issue #12: Revenue Growth Referenced But Never Used in Scoring
**Location**: `app/routers/screener.py:1310-1312`

**Problem**: `_generate_screening_reasons()` tries to use revenue_growth but:
1. It's not fetched by yfinance (Issue #2)
2. It's not used in score calculation (line 1184)
3. It's not in any screening filters

**Code**:
```python
# Line 1310-1312
revenue_growth = financials.get("revenue_growth", 0)
if revenue_growth and revenue_growth >= 15:
    reasons.append(f"Strong revenue growth ({revenue_growth:.1f}%)")
```

**Impact**:
- Dead code that never executes
- Creates false expectation that revenue growth is considered
- Incomplete feature

**Recommended Fix**:
```python
# Option 1: Remove dead code
# Delete lines 1310-1312

# Option 2: Implement revenue growth properly
# 1. Add revenue_growth to yfinance_provider.get_fundamentals()
# 2. Add revenue growth scoring to _calculate_lynch_score()
# 3. Add revenue_growth to FundamentalFilters model
```

**Priority**: MEDIUM - Dead code

---

### Issue #13: Excessive Logging May Impact Performance
**Location**: Throughout `screener.py`

**Problem**: Many `logger.info()` calls during screening loops:
```python
# Line 270
logger.info(f"✓ {ticker} passed screen (Score: {score:.1f})")  # Called for every passing stock
```

**Impact**:
- I/O overhead during high-volume screening
- Cluttered logs when screening large universes
- May slow down concurrent processing

**Recommended Fix**:
```python
# Option 1: Change to debug level for per-stock logs
logger.debug(f"✓ {ticker} passed screen (Score: {score:.1f})")

# Option 2: Batch logging
passing_tickers = [result.ticker for result in results]
logger.info(f"Passed screening: {', '.join(passing_tickers[:10])}... ({len(results)} total)")
```

**Priority**: MEDIUM - Performance optimization

---

### Issue #14: No Input Validation for universe Parameter
**Location**: `app/routers/screener.py:103-106, 932-936`

**Problem**: `universe` parameter accepts any string with no validation:
```python
universe: str = Query(
    "popular",
    description="Stock universe to screen (popular, sp500_sample, tech)",
)
```

**Impact**:
- Invalid universe values cause cryptic errors
- No API contract enforcement
- Documentation says 3 options but accepts anything

**Recommended Fix**:
```python
# Option 1: Use Enum
class StockUniverse(str, Enum):
    POPULAR = "popular"
    SP500_SAMPLE = "sp500_sample"
    TECH = "tech"
    NASDAQ = "nasdaq"
    NYSE = "nyse"
    ALL = "all"

universe: StockUniverse = Query(
    StockUniverse.POPULAR,
    description="Stock universe to screen",
)

# Option 2: Use regex pattern
universe: str = Query(
    "popular",
    regex="^(popular|sp500_sample|tech|nasdaq|nyse|all)$",
)
```

**Priority**: MEDIUM - Input validation

---

## 🟡 MEDIUM Priority (continued)

### Issue #15: Default FundamentalFilters Don't Match Presets
**Location**: `app/models/screener.py:309-339`

**Problem**: Default values in `FundamentalFilters` model don't match the actual presets used in endpoints:

**Model Defaults**:
```python
class FundamentalFilters(BaseModel):
    max_peg_ratio: Optional[float] = Field(1.0, ...)  # ❌ Fast Growers preset: 2.0
    min_eps_growth: Optional[float] = Field(15.0, ...)  # ✅ Matches
    max_eps_growth: Optional[float] = Field(30.0, ...)  # ❌ Fast Growers preset: None
    max_debt_to_equity: Optional[float] = Field(0.6, ...)  # ❌ Fast Growers preset: 0.8
    min_roe: Optional[float] = Field(15.0, ...)  # ✅ Matches
    max_institutional_ownership: Optional[float] = Field(30.0, ...)  # ❌ Fast Growers preset: None
```

**Fast Growers Preset** (screener.py:400-408):
```python
"filters": {
    "max_peg_ratio": 2.0,
    "min_eps_growth": 15.0,
    "max_eps_growth": None,
    "max_debt_to_equity": 0.8,
    "min_roe": 15.0,
    "max_institutional_ownership": None,
}
```

**Impact**:
- Users expect model defaults to align with presets
- Documentation inconsistency
- Default values are too strict and will return 0 results

**Recommended Fix**:
```python
# Option 1: Update model defaults to match Fast Growers preset
class FundamentalFilters(BaseModel):
    max_peg_ratio: Optional[float] = Field(2.0, ...)  # Match preset
    min_eps_growth: Optional[float] = Field(15.0, ...)
    max_eps_growth: Optional[float] = Field(None, ...)  # No upper limit
    max_debt_to_equity: Optional[float] = Field(0.8, ...)  # Match preset
    min_roe: Optional[float] = Field(15.0, ...)
    max_institutional_ownership: Optional[float] = Field(None, ...)  # No limit

# Option 2: Remove defaults entirely and require explicit values
# Option 3: Add note in docstring explaining defaults are example values
```

**Priority**: MEDIUM - Inconsistent defaults

---

## 🟢 LOW Priority

### Issue #16: Missing Type Hints in Helper Functions
**Location**: `app/routers/screener.py:621, 1184, 1256`

**Problem**: Some functions lack complete type hints:
```python
def _process_single_stock_technical(
    ticker: str,
    financials: dict,  # ❌ Should be dict[str, Any]
    request: AdvancedScreenerRequest,
    yf_provider: YFinanceProvider,
    gann_calc,  # ❌ Missing type hint
    pattern_detector,  # ❌ Missing type hint
    market_data: MarketDataProvider,
) -> Optional[StockScreenerResult]:
```

**Impact**:
- Reduced IDE autocomplete support
- Harder to catch type errors
- Inconsistent with rest of codebase

**Recommended Fix**:
```python
from ..financial_models.gann import GannCalculator
from ..financial_models.patterns import PatternDetector

def _process_single_stock_technical(
    ticker: str,
    financials: dict[str, Any],
    request: AdvancedScreenerRequest,
    yf_provider: YFinanceProvider,
    gann_calc: GannCalculator,
    pattern_detector: PatternDetector,
    market_data: MarketDataProvider,
) -> Optional[StockScreenerResult]:
```

**Priority**: LOW - Code quality

---

### Issue #16: Generic Exception Catching Without Re-raising
**Location**: `app/routers/screener.py:724-726, 729-735`

**Problem**: Broad exception handlers that silently fail:
```python
except Exception as e:
    logger.debug(f"Technical analysis failed for {ticker}: {e}")
    return None  # ❌ Silently fails, hard to debug
```

**Impact**:
- Hides unexpected errors
- Makes debugging difficult
- May mask serious bugs

**Recommended Fix**:
```python
# Option 1: Log at warning level with stack trace
except Exception as e:
    logger.warning(f"Technical analysis failed for {ticker}: {e}", exc_info=True)
    return None

# Option 2: Be more specific about exceptions
except (KeyError, ValueError, AttributeError) as e:
    logger.debug(f"Technical analysis failed for {ticker}: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error in technical analysis for {ticker}: {e}", exc_info=True)
    raise
```

**Priority**: LOW - Debugging improvement

---

### Issue #17: Hardcoded Market Regime VIX Thresholds
**Location**: `app/routers/screener.py:530-533` (referenced, not shown in code)

**Problem**: VIX thresholds likely hardcoded in yfinance_provider:
```python
# Likely in yfinance_provider.get_vix_data():
if vix < 20:
    regime = "low_fear"
elif vix < 30:
    regime = "moderate_fear"
else:
    regime = "high_fear"
```

**Impact**:
- No flexibility to adjust thresholds for different market conditions
- Thresholds may become outdated as markets evolve

**Recommended Fix**:
```python
# Make configurable via environment variables
VIX_LOW_FEAR_THRESHOLD = float(os.getenv("VIX_LOW_FEAR_THRESHOLD", "20"))
VIX_HIGH_FEAR_THRESHOLD = float(os.getenv("VIX_HIGH_FEAR_THRESHOLD", "30"))
```

**Priority**: LOW - Configuration flexibility

---

### Issue #18: Inconsistent Naming Convention (Fast Growers vs fast_growers)
**Location**: Throughout file

**Problem**: Mixed naming conventions for Lynch categories:
- Enum values: `fast_growers` (snake_case)
- Display names: `"Fast Growers"` (Title Case)
- Function names: `get_lynch_fast_growers` (snake_case)
- Screener name: `"Lynch Fast Growers"` (Title Case)

**Impact**:
- Inconsistency can cause confusion
- May lead to string comparison bugs

**Recommended Fix**:
```python
# Standardize on enum values for internal logic
# Use display_name property for user-facing strings

class LynchCategory(str, Enum):
    FAST_GROWERS = "fast_growers"

    @property
    def display_name(self) -> str:
        return self.value.replace('_', ' ').title()
```

**Priority**: LOW - Code consistency

---

## 📊 Summary Statistics

| Priority | Count | Percentage |
|----------|-------|------------|
| CRITICAL | 5 | 26.3% |
| HIGH | 4 | 21.1% |
| MEDIUM | 6 | 31.6% |
| LOW | 4 | 21.1% |
| **TOTAL** | **19** | **100%** |

---

## 🎯 Recommended Implementation Order

### Phase 1: Fix Critical Bugs (Issues #3, #5)
**Estimated Time**: 30 minutes
- Fix `price` → `current_price` field naming
- Fix `max_earnings_growth` None comparison
- Deploy hotfix immediately

### Phase 2: Complete yfinance Migration (Issues #1, #2, #4, #9)
**Estimated Time**: 2-3 hours
- Remove all MarketDataProvider usage
- Add missing fields (PE ratio, revenue growth, 52-week low)
- Consolidate company name fetching logic
- Test thoroughly with all endpoints

### Phase 3: Fix High Priority Issues (Issues #6, #7, #8)
**Estimated Time**: 1-2 hours
- Update documentation in `/screeners` endpoint
- Fix exception handling
- Verify/implement `get_stock_universe()` in yfinance provider

### Phase 4: Address Medium Priority Issues (Issues #10-15)
**Estimated Time**: 2-4 hours
- Make technical stock limit configurable
- Clean up dead code
- Add input validation
- Optimize logging
- Update FundamentalFilters defaults to match presets

### Phase 5: Polish (Issues #16-19)
**Estimated Time**: 1-2 hours
- Add complete type hints
- Improve exception handling
- Make VIX thresholds configurable
- Standardize naming conventions

---

## 🧪 Testing Checklist

After implementing fixes, test:

- [ ] Lynch Fast Growers endpoint with all presets
- [ ] Advanced screener with technical filters
- [ ] Advanced screener with Gann location filters
- [ ] Market regime filtering
- [ ] All 6 Lynch category presets
- [ ] Edge cases: None values, missing data, invalid tickers
- [ ] Performance: Screen 100+ stocks concurrently
- [ ] Error handling: Network failures, invalid inputs

---

## 📝 Additional Recommendations

### Consider Creating:
1. **YFinanceProvider Unit Tests**: Cover all methods with edge cases
2. **Stock Universe Management Module**: Centralize stock list logic
3. **Field Mapping Documentation**: Document yfinance → API response mapping
4. **Performance Benchmarks**: Track screening speed over time
5. **Migration Guide**: Document Polygon → yfinance changes for users

### Architecture Improvements:
1. **Separate Data Layer**: Create abstract DataProvider interface
2. **Caching Strategy**: Cache fundamentals for 1 hour to reduce API calls
3. **Rate Limiting**: Add explicit rate limiting for yfinance calls
4. **Health Checks**: Add endpoint to verify yfinance connectivity
5. **Metrics Collection**: Track screening performance and success rates

---

---

## 🔴 NEW ISSUES (2025-11-10)

### Issue #19: Smart Money & The Undiscovered Validation Errors (FIXED)
**Location**: `app/routers/screener.py:458-472, 641-656`
**Status**: ✅ RESOLVED in v2.4.1-screeners-fix

**Problem**: Both new screeners were returning HTTP 500 errors with Pydantic validation failures:
```
3 validation errors for ScreenerResponse
screener_name - Field required
description - Field required
```

**Root Cause**: Endpoints used incorrect field names not matching the `ScreenerResponse` model:
- Used `total_stocks_screened` instead of storing in `criteria`
- Used `stocks_passed` instead of `total_results`
- Used `stocks_failed` instead of storing in `criteria`
- Used `execution_time_seconds` instead of storing in `criteria`
- Used ISO string `timestamp` instead of datetime object

**Fix Applied**:
```python
# ✅ CORRECTED
return ScreenerResponse(
    screener_name="Smart Money",
    description=f"Options-driven screener tracking institutional conviction...",
    total_results=len(results),
    results=results,
    timestamp=datetime.now(),
    criteria={
        "min_call_to_put_ratio": min_call_to_put_ratio,
        "total_stocks_screened": len(stock_universe),
        "stocks_failed": len(failed_tickers),
        "execution_time_seconds": round(execution_time, 2),
        ...
    },
)
```

**Deployed**: Backend revision `prod-backend-api-00021-gwq` (2025-11-10)

---

### Issue #20: Frontend Timeout Exceeded (FIXED)
**Location**: `frontend/src/config/api.ts:15`
**Status**: ✅ RESOLVED

**Problem**: Screeners were failing with:
```
API Error: undefined timeout of 30000ms exceeded
Screening error: zt
```

**Root Cause**:
- Screeners take 35-40 seconds to complete (fetching options/institutional data for 46 stocks)
- Frontend axios client had 30-second timeout
- Each stock requires multiple yfinance API calls with 0.2s rate limiting

**Execution Times** (from Cloud Run logs):
- Smart Money: ~35-40 seconds for 46 stocks
- The Undiscovered: ~38 seconds for 46 stocks

**Fix Applied**:
```typescript
// frontend/src/config/api.ts
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // Increased from 30000 to 120000 (2 minutes)
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**Deployed**: Frontend to Firebase Hosting (2025-11-10)

**Performance Notes**:
- Each screener processes 46 stocks serially
- Each stock requires 2-3 yfinance API calls:
  - `get_fundamentals()` - Basic financial data
  - `get_options_flow_metrics()` - Options volume/call-put ratio (Smart Money)
  - `get_analyst_and_insider_data()` - Analyst count/insider transactions (Undiscovered)
- Rate limiting: 0.2s between calls to respect yfinance API limits
- Total time: 46 stocks × ~0.8s per stock ≈ 37 seconds

**Future Optimizations** (optional):
1. Reduce default universe to 20-30 stocks
2. Add caching (5-15 min TTL for options/institutional data)
3. Parallelize API calls with rate limiting (asyncio)
4. Use smaller "tech" universe (31 stocks) as default instead of "popular" (46 stocks)

---

**Generated by**: Claude Code
**Review Date**: 2025-11-08 (original), 2025-11-10 (updated)
**Code Version**: v3.1.2-relaxed-presets (original), v2.4.1-screeners-fix (latest)
