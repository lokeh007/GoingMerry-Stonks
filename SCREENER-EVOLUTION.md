# Stock Screener Evolution - Implementation Tracking

**Last Updated**: November 8, 2025
**Status**: 🚧 In Progress
**Current Phase**: Phase 1 - Foundation & Lynch Fast Growers

---

## Overview

This document tracks the incremental development of the Stock Screener page - a comprehensive multi-layered stock analysis tool combining Peter Lynch fundamentals, technical analysis patterns (Bulkowski), and Gann theory.

### Design Philosophy

The screener uses a **funnel approach**:
1. **Section 1 (Lynch Fundamentals)**: Filter 5,000+ stocks → 50-100 fundamentally sound companies
2. **Section 2 (Technical Triggers)**: Filter for timing using RSI, MACD, patterns, Gann levels → 10-20 stocks
3. **Section 3 (Market Context)**: Validate against market regime (VIX) → Final watchlist
4. **Section 4 (Results Grid)**: Interactive table with click-through to Technical Analysis and Options pages

---

## Implementation Phases

### ✅ Phase 0: Planning & Setup
- [x] Create SCREENER-EVOLUTION.md tracking document
- [ ] Review existing screener implementation (`backend/app/routers/screener.py`)
- [ ] Review existing frontend pages (Technical Analysis, Options)
- [ ] Design data flow architecture

### 🚧 Phase 1: Backend Foundation (Current)
**Goal**: Extend existing Lynch Fast Growers screener with enhanced data sources

#### 1.1 Data Layer - yfinance Integration
- [ ] Add `yfinance` to `backend/requirements.txt`
- [ ] Create `backend/app/services/yfinance_provider.py`:
  - [ ] Fetch NYSE + NASDAQ ticker universe
  - [ ] Fetch technical indicators (RSI, MACD)
  - [ ] Fetch VIX data
  - [ ] Fetch historical OHLCV for pattern detection
  - [ ] Implement caching (15-min TTL to match data delay)
  - [ ] Error handling and rate limiting

#### 1.2 Financial Calculations
- [ ] Create `backend/app/financial_models/gann.py`:
  - [ ] Implement Square of 9 spiral calculation
  - [ ] Calculate support/resistance levels (90°, 180°, 270°, 360°)
  - [ ] Find current price position relative to Gann levels
- [ ] Create `backend/app/financial_models/patterns.py`:
  - [ ] Pipe Bottom detector (two parallel sharp lows)
  - [ ] Double Bottom detector (return to test major low)
  - [ ] Pattern precondition filters

#### 1.3 Enhanced Data Models
- [ ] Update `backend/app/models/screener.py`:
  - [ ] Add `LynchCategory` enum (Fast Growers, Stalwarts, Slow Growers, Cyclicals, Turnarounds, Asset Plays)
  - [ ] Add `TechnicalIndicators` model (RSI, MACD, MACD Signal, MACD Histogram)
  - [ ] Add `BulkowskiPattern` enum and detection fields
  - [ ] Add `GannLevels` model (support levels, resistance levels, current position)
  - [ ] Add `MarketRegime` enum (Any, Low Fear, High Fear)
  - [ ] Enhance `StockScreenerResult` with all new fields

#### 1.4 Screener Router Enhancement
- [ ] Update `backend/app/routers/screener.py`:
  - [ ] Add `/screener/universe` endpoint (get available tickers with pagination)
  - [ ] Enhance `/screener/lynch-fast-growers` with new fields
  - [ ] Add `/screener/advanced` endpoint with all 4 sections:
    - [ ] Lynch category-based filter presets
    - [ ] Technical trigger filters
    - [ ] Market regime filter
    - [ ] Pagination support (page size: 50)
  - [ ] Add `/screener/presets/{category}` to get recommended filters per Lynch category

#### 1.5 Testing
- [ ] Unit tests for Gann Square of 9 calculations
- [ ] Unit tests for pattern detection
- [ ] Integration test for yfinance provider
- [ ] Integration test for advanced screener endpoint

### 📋 Phase 2: Frontend - Basic UI
**Goal**: Build interactive screener page with Section 1 (Lynch) and Section 4 (Results)

#### 2.1 Component Structure
- [ ] Create `frontend/src/components/StockScreener.tsx` (main container)
- [ ] Create `frontend/src/components/screener/LynchFilters.tsx` (Section 1)
- [ ] Create `frontend/src/components/screener/ScreenerResults.tsx` (Section 4)
- [ ] Create `frontend/src/types/screener.ts` (TypeScript types)
- [ ] Create `frontend/src/utils/screenerApi.ts` (API calls)

#### 2.2 Section 1: Lynch Fundamental Filters
- [ ] Lynch Category dropdown with 6 options
- [ ] Auto-populate filters based on category selection:
  - [ ] PEG Ratio slider (0.1 - 3.0, default: < 1.0)
  - [ ] EPS Growth range (0% - 50%, default: 15% - 30%)
  - [ ] Debt-to-Equity slider (0 - 2.0, default: < 0.6)
  - [ ] ROE slider (0% - 50%, default: > 15%)
  - [ ] Institutional Ownership slider (0% - 100%, default: < 30%)
  - [ ] Market Cap filter (optional minimum)

#### 2.3 Section 4: Results Grid
- [ ] Interactive table with columns:
  - Ticker, Company Name, Sector, Market Cap
  - PEG Ratio, EPS Growth, D/E, ROE
  - Current Price, % Change
- [ ] Pagination controls (50 results per page)
- [ ] Click ticker → navigate to Technical Analysis or Options page
- [ ] Export to CSV functionality
- [ ] Loading states and error handling

#### 2.4 Basic Interactions
- [ ] "RUN SCREEN" button
- [ ] Loading spinner during API call
- [ ] Results counter ("Showing X of Y stocks")
- [ ] Reset filters button

### 📋 Phase 3: Frontend - Advanced Filters
**Goal**: Add Section 2 (Technical Triggers) and Section 3 (Market Context)

#### 3.1 Section 2: Technical Trigger Filters
- [ ] Create `frontend/src/components/screener/TechnicalFilters.tsx`
- [ ] Momentum Indicators:
  - [ ] RSI dropdown: Any, Oversold (< 30), Neutral (30-70), Overbought (> 70)
  - [ ] MACD dropdown: Any, Bullish Crossover, Bearish Crossover
- [ ] Bulkowski Pattern Pre-Screener:
  - [ ] Pattern Setup dropdown: Any, Potential Pipe Bottom, Potential Double Bottom
- [ ] Gann Level Screener:
  - [ ] Gann Location dropdown: Any, At Key Support, At Key Resistance

#### 3.2 Section 3: Market Context Filter
- [ ] Create `frontend/src/components/screener/MarketContextFilter.tsx`
- [ ] VIX-based Market Regime selector:
  - [ ] Options: Any, Low Fear (VIX < 20), High Fear (VIX > 30)
  - [ ] Display current VIX value and regime

#### 3.3 Enhanced Results Grid
- [ ] Add technical indicator columns (RSI, MACD)
- [ ] Add pattern detection badges
- [ ] Add Gann level indicators (color-coded: green for support, red for resistance)
- [ ] Sorting by any column
- [ ] Multi-column sorting

### 📋 Phase 4: Firebase Integration & Persistence
**Goal**: Add Cloud Firestore for configuration storage and result caching

#### 4.1 Firebase Setup
- [ ] Add Firebase configuration to frontend
- [ ] Create Firestore collections:
  - `screener_configs`: User-saved filter configurations
  - `screener_results_cache`: Cached screening results (TTL: 15 min)
- [ ] Add Firebase Admin SDK to backend (optional, for server-side caching)

#### 4.2 Save/Load Screener Configurations
- [ ] "Save Configuration" button → modal to name and save current filters
- [ ] "Load Configuration" dropdown → populate filters from saved config
- [ ] "My Saved Screeners" section → list of user's saved configs
- [ ] Delete saved configuration

#### 4.3 Results Caching
- [ ] Cache screening results in Firestore (keyed by filter hash)
- [ ] Check cache before running API call
- [ ] Display cache timestamp and "Refresh" button
- [ ] Auto-refresh after 15 minutes

### 📋 Phase 5: URL Sharing & Navigation
**Goal**: Enable shareable screener configurations and seamless navigation

#### 5.1 URL Parameter Encoding
- [ ] Encode filter state in URL query parameters
- [ ] Parse URL parameters on component mount
- [ ] Update URL when filters change (debounced)
- [ ] Share button → copy URL to clipboard

#### 5.2 Navigation Integration
- [ ] Update `frontend/src/App.tsx` to make StockScreener default route
- [ ] Pass selected ticker to Technical Analysis page via URL params
- [ ] Pass selected ticker to Options page via URL params
- [ ] Breadcrumb navigation (Screener → Technical Analysis / Options)
- [ ] "Back to Screener" button on detail pages

### 📋 Phase 6: Polish & Optimization
**Goal**: Production-ready performance and UX

#### 6.1 Performance Optimization
- [ ] Implement request debouncing (don't run screen on every filter change)
- [ ] Add pagination on backend (limit database queries)
- [ ] Optimize yfinance batch fetching
- [ ] Add server-side caching layer (Redis or similar)
- [ ] Lazy-load technical indicators (only fetch when Section 2 is used)

#### 6.2 UX Enhancements
- [ ] Filter presets for common strategies:
  - "Classic Lynch Fast Growers"
  - "Deep Value in Market Panic" (High Fear + Oversold RSI)
  - "Momentum Breakouts" (Low Fear + MACD Bullish)
- [ ] Tooltips explaining each filter (e.g., "What is PEG Ratio?")
- [ ] Mobile-responsive design
- [ ] Dark mode support
- [ ] Keyboard shortcuts (Enter to run screen, Esc to reset)

#### 6.3 Documentation
- [ ] Update `CLAUDE.md` with Stock Screener documentation
- [ ] Create `frontend/STOCK_SCREENER_GUIDE.md` with user guide
- [ ] Add API documentation for screener endpoints
- [ ] Update README.md with screener feature

#### 6.4 Testing
- [ ] Frontend unit tests (Jest + React Testing Library)
- [ ] E2E tests (Cypress or Playwright)
- [ ] Load testing (screen 5,000 stocks with all filters)
- [ ] Cross-browser testing

---

## Data Sources

### Current (Polygon.io)
- ✅ Stock quotes and prices
- ✅ Company fundamentals (P/E, PEG, D/E, ROE)
- ✅ Options data
- ❌ Technical indicators (not directly available)
- ❌ Pattern detection (not available)

### New (yfinance)
- ✅ Technical indicators (RSI, MACD) - 15-min delayed
- ✅ Historical OHLCV for pattern detection
- ✅ VIX data
- ✅ Expanded ticker universe (NYSE + NASDAQ)
- ✅ Free tier, no rate limits

### Calculated In-App
- ✅ Gann Square of 9 levels
- ✅ Bulkowski pattern preconditions
- ✅ Lynch scoring algorithm

---

## Lynch Category Filter Presets

| Category | PEG | EPS Growth | D/E | ROE | Inst. Own | Focus |
|----------|-----|------------|-----|-----|-----------|-------|
| **Fast Growers** | < 1.0 | 15-30% | < 0.6 | > 15% | < 30% | Rapid growth at reasonable price |
| **Stalwarts** | < 1.5 | 10-15% | < 0.8 | > 12% | Any | Large, reliable companies on sale |
| **Slow Growers** | Any | < 10% | < 1.0 | > 8% | Any | High dividend, stable (focus on yield) |
| **Cyclicals** | < 1.0 | Any | < 1.0 | Positive | Any | Timing business cycle (inventory focus) |
| **Turnarounds** | Any | Negative OK | < 0.5 | Any | Any | Balance sheet health (cash > debt) |
| **Asset Plays** | Any | Any | < 0.5 | Any | < 50% | Hidden value (book value > market cap) |

---

## Technical Implementation Notes

### Gann Square of 9 Algorithm
```python
def calculate_gann_square(price: float) -> dict:
    """
    Calculate Gann Square of 9 support and resistance levels.

    The Square of 9 is a spiral starting at 1 in the center.
    Key angles: 90°, 180°, 270°, 360° (full rotation)

    Formula: value = (sqrt(start) + angle/360)^2
    """
    # Implementation in backend/app/financial_models/gann.py
```

### Bulkowski Pattern Detection
```python
def detect_pipe_bottom(df: pd.DataFrame) -> bool:
    """
    Pipe Bottom: Two sharp, parallel-day lows

    Criteria:
    - Two trading days with lows within 2% of each other
    - Days separated by 1-5 trading days
    - Sharp decline before first low (> 5% in 3 days)
    """
    # Implementation in backend/app/financial_models/patterns.py
```

### yfinance Batch Fetching Strategy
```python
# Fetch data in batches of 100 tickers to avoid timeouts
# Use ThreadPoolExecutor for parallel requests
# Cache results in memory for 15 minutes
```

---

## API Endpoints (New/Updated)

### GET `/api/screener/universe`
**Purpose**: Get paginated list of available tickers
**Query Params**: `page` (int), `page_size` (int, default 1000), `exchange` (NYSE, NASDAQ, ALL)
**Response**: `{ "tickers": ["AAPL", "MSFT", ...], "total": 5234, "page": 1, "page_size": 1000 }`

### POST `/api/screener/advanced`
**Purpose**: Run advanced multi-layered screen
**Request Body**:
```json
{
  "lynch_category": "fast_growers",
  "fundamental_filters": {
    "max_peg_ratio": 1.0,
    "min_eps_growth": 15,
    "max_eps_growth": 30,
    "max_debt_to_equity": 0.6,
    "min_roe": 15,
    "max_institutional_ownership": 30
  },
  "technical_filters": {
    "rsi_condition": "oversold",
    "macd_condition": "bullish_crossover",
    "pattern": "pipe_bottom",
    "gann_location": "at_support"
  },
  "market_regime": "high_fear",
  "page": 1,
  "page_size": 50
}
```
**Response**: Paginated list of `StockScreenerResult` objects

### GET `/api/screener/presets/{category}`
**Purpose**: Get recommended filter settings for a Lynch category
**Path Params**: `category` (fast_growers, stalwarts, slow_growers, cyclicals, turnarounds, asset_plays)
**Response**: Filter preset object

---

## Frontend Component Hierarchy

```
StockScreener (Container)
├── ScreenerHeader (Title, description, saved configs dropdown)
├── ScreenerFilters (The 3 filter sections)
│   ├── LynchFilters (Section 1)
│   │   ├── LynchCategorySelector
│   │   ├── PEGRatioSlider
│   │   ├── EPSGrowthRangeSlider
│   │   ├── DebtToEquitySlider
│   │   ├── ROESlider
│   │   └── InstitutionalOwnershipSlider
│   ├── TechnicalFilters (Section 2)
│   │   ├── RSIFilter
│   │   ├── MACDFilter
│   │   ├── PatternFilter
│   │   └── GannLevelFilter
│   └── MarketContextFilter (Section 3)
│       └── VIXRegimeSelector
├── ScreenerActions
│   ├── RunScreenButton (Primary CTA)
│   ├── ResetFiltersButton
│   ├── SaveConfigButton
│   └── ShareButton (Copy URL)
└── ScreenerResults (Section 4)
    ├── ResultsHeader (Count, filters applied, export)
    ├── ResultsTable (Interactive grid)
    │   ├── SortableHeader
    │   ├── ResultRow (Click → navigate to detail page)
    │   └── Pagination
    └── EmptyState (No results / Initial state)
```

---

## Progress Tracking

### Current Sprint Goals
- [ ] Complete Phase 1.1: yfinance Integration
- [ ] Complete Phase 1.2: Gann & Pattern Calculations
- [ ] Complete Phase 1.3: Enhanced Data Models

### Completed Milestones
- [x] Planning & architecture design
- [x] Created SCREENER-EVOLUTION.md tracking document

### Blockers & Decisions Needed
- None currently

---

## Future Enhancements (Post-MVP)

1. **Watchlist Integration**: Save screened stocks to personal watchlists
2. **Alerts**: Email/SMS when new stocks pass your saved screener
3. **Backtesting**: "Run this screen historically" to see past performance
4. **AI Insights**: GPT-4 analysis of why a stock passed the screen
5. **Community Screeners**: Share and discover screeners from other users
6. **Advanced Patterns**: Add more Bulkowski patterns (Cup-and-Handle, Head-and-Shoulders, etc.)
7. **Sector Rotation**: Add sector performance overlay
8. **Earnings Calendar Integration**: Filter by upcoming earnings dates
9. **Insider Trading Filter**: Stocks with recent insider buying
10. **Short Interest Filter**: Stocks with high short interest (potential squeeze candidates)

---

## References

- **Peter Lynch Books**: "One Up On Wall Street", "Beating the Street"
- **Bulkowski's Pattern Site**: http://thepatternsite.com
- **Gann Theory**: "How to Make Profits Trading in Commodities" by W.D. Gann
- **yfinance Docs**: https://github.com/ranaroussi/yfinance
- **Firebase Firestore**: https://firebase.google.com/docs/firestore

---

**Note**: This is a living document. Update status and checkboxes as implementation progresses.
