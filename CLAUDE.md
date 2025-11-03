# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GoingMerry-Stonks is a full-stack financial analysis platform for options trading and stock screening. The application consists of a FastAPI backend serving market data from Polygon.io and a React/TypeScript frontend for visualization and analysis.

## Development Setup

### Backend (Python/FastAPI)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create .env file with: POLYGON_API_KEY=your_api_key_here

# Run development server
uvicorn app.main:app --reload

# Server runs at: http://localhost:8000
# API docs at: http://localhost:8000/api/docs
```

### Frontend (React/TypeScript)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start

# Frontend runs at: http://localhost:3000
```

### Testing

```bash
# Backend API connectivity test
python backend/test_api.py

# Test screener endpoints
python backend/test_screener.py
python backend/test_real_screener.py

# Test options endpoints
python backend/test_options_endpoint.py

# Frontend tests
cd frontend && npm test
```

## Architecture

### Backend Structure

The backend follows a clean, modular FastAPI architecture with separation of concerns:

- **`app/main.py`** - FastAPI application entry point, CORS configuration, router registration
- **`app/routers/`** - API endpoint definitions
  - `options.py` - Options chain endpoints (`GET /options/{ticker}`, `/options/{ticker}/summary`)
  - `screener.py` - Stock screening endpoints (`GET /screener/lynch-fast-growers`, `/screener/screeners`)
- **`app/models/`** - Pydantic models for request/response validation
  - `options.py` - OptionContract, OptionChainResponse, OptionType enum
  - `screener.py` - StockScreenerResult, ScreenerResponse, ScreenerCriteria
- **`app/services/`** - Business logic and external integrations
  - `market_data.py` - **MarketDataProvider class**: Centralized Polygon.io API client with methods for stock quotes, option chains, financials, and ticker details. All external API calls go through this service.
- **`app/financial_models/`** - Financial calculations
  - `options_pricing.py` - Black-Scholes-Merton pricing model and Greeks calculations

**Key Integration Point**: The `MarketDataProvider` in `backend/app/services/market_data.py` is the single source of truth for all market data. It handles:
- Stock quotes and current prices
- Option chain data with Greeks
- Financial fundamentals (P/E, PEG, debt ratios, growth rates)
- Ticker details (company name, sector, market cap)
- Stock universes for screening (popular, sp500_sample, tech)
- Error handling for API issues (rate limits, invalid tickers, connection errors)

### Frontend Structure

The frontend uses a component-based architecture with TypeScript for type safety:

- **`src/components/`** - React components
  - `OptionsAnalyzer.tsx` - Main container orchestrating options analysis workflow
  - `OptionsGrid.tsx` - Interactive grid displaying option chain (strikes × expirations)
  - `MetricsDisplay.tsx` - Financial metrics cards (P/L, ROC, breakeven, collateral)
  - `ProfitLossChart.tsx` - Chart.js visualization showing strategy P/L curves
  - `PLChartExample.tsx` - Standalone P/L chart demo
  - `MetricsExample.tsx` - Standalone metrics display demo
- **`src/utils/`** - Pure calculation functions
  - `optionsDataTransform.ts` - Transforms API data for grid display
  - `metricsCalculator.ts` - Calculates financial metrics for options strategies
  - `profitLossCalculator.ts` - Generates P/L data points for charting
- **`src/types/`** - TypeScript type definitions
  - `options.ts` - OptionData, OptionChainData, StrategyType
  - `metrics.ts` - FinancialMetrics interface

**Data Flow**: API Response → optionsDataTransform → OptionsGrid → User Selection → metricsCalculator + profitLossCalculator → MetricsDisplay + ProfitLossChart

### Key Technical Patterns

**Backend**:
- **Singleton MarketDataProvider**: Initialized once per router, reused across requests
- **Custom Exception Hierarchy**: MarketDataError → InvalidTickerError, APIConnectionError, RateLimitError mapped to appropriate HTTP status codes
- **Async/Await**: All router endpoints are async for non-blocking I/O
- **Pydantic Validation**: Automatic request/response validation with detailed error messages
- **Comprehensive Logging**: All service methods log at INFO level for debugging

**Frontend**:
- **Controlled Components**: Parent components manage state, children receive props
- **Type Safety**: Full TypeScript coverage with interfaces for all data structures
- **Separation of Concerns**: Display components (TSX) separate from calculation logic (utils)
- **Chart.js Integration**: ProfitLossChart uses react-chartjs-2 wrapper with custom options

## Alpha Engine - Stock Screener

The screener system (documented in `backend/ALPHA_ENGINE_GUIDE.md`) implements Peter Lynch's "Fast Growers" strategy:

**Screening Criteria**:
- EPS Growth: 15-30% annually (configurable via `min_earnings_growth`, `max_earnings_growth`)
- PEG Ratio: < 1.0 (configurable via `max_peg_ratio`)
- Debt-to-Equity: < 0.5 (configurable via `max_debt_to_equity`)
- Current Ratio: ≥ 1.0 (configurable via `min_current_ratio`)
- Market Cap: ≥ $1B (configurable via `min_market_cap`)

**Scoring Algorithm** (0-100 scale):
- PEG Ratio (40 points): < 0.5 = 40pts, 0.5-0.75 = 30pts, 0.75-1.0 = 20pts
- EPS Growth (30 points): 20-25% = 30pts, 15-20% = 25pts, 25-30% = 25pts
- Debt-to-Equity (20 points): < 0.25 = 20pts, 0.25-0.5 = 15pts, 0.5-1.0 = 10pts
- Current Ratio (10 points): ≥ 2.5 = 10pts, 2.0-2.5 = 8pts, 1.5-2.0 = 6pts

See `_calculate_lynch_score()` in `backend/app/routers/screener.py:352` for implementation.

**Stock Universes**: Defined in `MarketDataProvider.get_stock_universe()` at `backend/app/services/market_data.py:704`:
- `popular`: 46 large-cap stocks across sectors
- `sp500_sample`: 41 S&P 500 constituents
- `tech`: 31 technology sector stocks

## Options Analysis Components

**Supported Strategies** (in `frontend/src/utils/metricsCalculator.ts`):
- `long_call`: Bullish, pay premium, unlimited upside
- `long_put`: Bearish, pay premium, limited risk
- `short_call`: Bearish, collect premium, risk assignment
- `short_put`: Bullish, collect premium, cash-secured

**Greeks Calculation**: Black-Scholes-Merton model in `backend/app/financial_models/options_pricing.py` calculates Delta, Theta, Gamma, Vega, Rho.

**P/L Chart Features**:
- Generates 100 price points from 50% below to 50% above current price
- Automatic breakeven detection using sign change algorithm
- Color-coded profit (green) and loss (red) zones
- Hover tooltips showing exact P/L at each price point
- Breakeven markers with vertical dashed lines

## Environment Configuration

### Backend `.env` File (required)

```bash
POLYGON_API_KEY=your_polygon_api_key_here
```

**Polygon.io API Notes**:
- Free tier: 5 calls/minute, 15-minute delayed data
- Options snapshots are rate-limited (limited to 50 contracts in `get_option_chain()`)
- Financials endpoint requires paid tier for real-time data

### Frontend Proxy

`package.json` includes `"proxy": "http://localhost:8000"` to avoid CORS issues during development.

### CORS Configuration

Backend allows `http://localhost:3000` by default. Modify in `backend/app/main.py:25-31` for production.

## Common Development Tasks

### Adding a New Screener

1. Define screening logic in new router function in `backend/app/routers/screener.py`
2. Use `MarketDataProvider.get_stock_financials()` to fetch data
3. Implement scoring function similar to `_calculate_lynch_score()`
4. Add to `/screener/screeners` endpoint list
5. Document criteria and scoring in `backend/ALPHA_ENGINE_GUIDE.md`

### Adding a New Options Strategy

1. Add strategy type to `StrategyType` union in `frontend/src/types/options.ts`
2. Implement P/L calculation in `frontend/src/utils/profitLossCalculator.ts`
3. Add metrics calculation in `frontend/src/utils/metricsCalculator.ts`
4. Update strategy selector in `OptionsAnalyzer.tsx`

### Debugging API Issues

- Check Polygon.io API key in `.env`
- Monitor rate limits in backend logs
- Use `python backend/test_api.py` to verify connectivity
- Check API docs at http://localhost:8000/api/docs for request/response schemas

### Working with Financial Data

All financial calculations should use the data returned by `MarketDataProvider.get_stock_financials()`. This method:
- Fetches 4 quarters of financial statements from Polygon.io
- Calculates growth rates (EPS, revenue) comparing Q0 vs Q-4
- Computes ratios (P/E, PEG, D/E, current ratio)
- Returns None for missing data (handle gracefully in screening logic)

Growth rate calculation: `((current - old) / abs(old)) * 100`

## File Naming and Organization

- Backend: Snake_case for Python files (`market_data.py`, `options_pricing.py`)
- Frontend: PascalCase for components (`OptionsGrid.tsx`), camelCase for utilities (`metricsCalculator.ts`)
- Models match their domain: `options.py` for options models, `screener.py` for screener models
- Test files prefixed with `test_` and colocated in `backend/` directory

## Important Notes

- **Never commit `.env` files**: Contains API keys
- **Polygon.io Limitations**: Free tier has strict rate limits; consider caching for production
- **Options Data**: Option snapshots may be incomplete for low-volume contracts
- **Type Safety**: Always define TypeScript interfaces for new data structures
- **Error Handling**: Backend uses custom exceptions; frontend should handle HTTP errors gracefully
- **Logging**: Use `logger.info()` for key operations, `logger.warning()` for recoverable errors, `logger.error()` for failures

## Additional Documentation

- `backend/ALPHA_ENGINE_GUIDE.md` - Comprehensive screener documentation with examples
- `frontend/COMPONENTS.md` - Component API reference
- `frontend/INTEGRATION_GUIDE.md` - Frontend integration patterns
- `frontend/PROFIT_LOSS_CHART_GUIDE.md` - P/L chart usage and customization
- API Interactive Docs: http://localhost:8000/api/docs (Swagger UI)
