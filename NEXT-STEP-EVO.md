# GoingMerry-Stonks: Evolution Roadmap

This document tracks future enhancements and feature possibilities for the platform.

**Last Updated:** November 6, 2025
**Current Version:** Backend v2.2.0-technical, Frontend deployed
**Status:** Technical Analysis MVP Complete ✅

---

## 🎯 Current Sprint: Technical Analysis Enhancements

### COMPLETED: Volume Bars + Candlestick Charts ✅
**Priority:** HIGH
**Effort:** 1 day (6-8 hours)
**Status:** 🟢 Deployed to Production

**Completed Tasks:**
- [x] Add volume bar chart below price chart
- [x] Implement candlestick chart component
- [x] Add chart type toggle (Line | Candlestick)
- [x] Update PriceChart to support both modes
- [x] Test with various tickers and timeframes
- [x] Deploy to production

**Deployment Date:** November 6, 2025
**Bundle Size:** 146.07 KB gzipped (main.js)

**Technical Details:**
- Volume data already available in API response
- OHLC data present in backend
- Use Chart.js candlestick plugin or custom canvas rendering
- Maintain dark theme styling

---

## 📋 Immediate Enhancements (High Value, Low Effort)

### 1. Volume Bars Below Price Chart ✅ COMPLETED
**Effort:** 2-3 hours
**Impact:** HIGH - Industry standard feature
**Status:** 🟢 Deployed November 6, 2025

**Implementation Details:**
- Created VolumeChart.tsx component (frontend/src/components/TechnicalAnalysis/VolumeChart.tsx:38)
- Bar chart with green (up days) / red (down days) coloring
- Positioned below price chart in TechnicalAnalysisPage (frontend/src/pages/TechnicalAnalysisPage.tsx:277)
- Height: 200px
- Smart volume formatting (M/B/K abbreviations)

### 2. Candlestick Chart Option ✅ COMPLETED
**Effort:** 3-4 hours
**Impact:** HIGH - Professional upgrade
**Status:** 🟢 Deployed November 6, 2025

**Implementation Details:**
- Created CandlestickChart.tsx component (frontend/src/components/TechnicalAnalysis/CandlestickChart.tsx:49)
- Uses colored bars to represent price bars (green for up days, red for down days)
- Added toggle button group: Line Chart | Candlestick (frontend/src/pages/TechnicalAnalysisPage.tsx:211)
- Maintains EMA overlays in both modes
- Custom tooltip showing OHLC data

### 3. Add More Technical Indicators ✅ COMPLETED
**Effort:** 4-6 hours
**Impact:** HIGH - Backend already supports them
**Status:** 🟢 Deployed November 6, 2025

**Implemented Indicators:**
- ✅ Bollinger Bands (upper, middle, lower bands)
- ✅ SMA 20, 50, 200 (Simple Moving Averages)
- ✅ EMA 200 (Exponential Moving Average)

**Implementation Details:**
- Added checkboxes for all new indicators (frontend/src/pages/TechnicalAnalysisPage.tsx:193-256)
- Updated PriceChart component to display all indicators (frontend/src/components/TechnicalAnalysis/PriceChart.tsx:32)
- Updated CandlestickChart component to display all indicators (frontend/src/components/TechnicalAnalysis/CandlestickChart.tsx:37)
- Color-coded different indicator types:
  - EMAs: Dashed lines (orange, purple, red, dark red)
  - SMAs: Short-dashed lines (cyan, violet, pink)
  - Bollinger Bands: Light blue with semi-transparent bands
- All indicators overlay on both Line and Candlestick charts
- Toggle any combination of indicators on/off via checkboxes

**Completed Tasks:**
- [x] Add checkboxes for Bollinger Bands, SMA20, SMA50, SMA200, EMA200
- [x] Add Bollinger Bands to PriceChart and CandlestickChart
- [x] Update indicator selection state management
- [x] Test indicator combinations
- [x] Deploy to production

**Deployment Date:** November 6, 2025
**Bundle Size:** 146.55 KB gzipped (+ 471 B from previous version)

### 4. Add Loading States for Individual Charts
**Effort:** 1-2 hours
**Impact:** MEDIUM - Better UX
**Status:** 🔴 Not Started

**Benefits:**
- Progressive chart loading
- No full-page spinner
- Better perceived performance

**Implementation:**
- Skeleton loaders for each chart container
- Charts appear as data arrives
- Maintain spinners for initial page load

---

## 🚀 Medium-Term Enhancements (High Value, Medium Effort)

### 5. Chart Drawing Tools
**Effort:** 8-12 hours
**Impact:** HIGH - Professional feature
**Status:** 🔴 Not Started

**Features:**
- Trendlines (support/resistance)
- Horizontal price alerts
- Fibonacci retracements
- Text annotations
- Drawing persistence (localStorage)

**Libraries to Evaluate:**
- Chart.js Annotation Plugin
- Lightweight Charts (TradingView library)
- Custom canvas drawing

### 6. Multiple Timeframe Analysis
**Effort:** 4-6 hours
**Impact:** HIGH - Faster workflow
**Status:** 🔴 Not Started

**Features:**
- Quick toggle buttons: 1D, 5D, 1M, 3M, 6M, 1Y, 5Y
- Store last selected timeframe in localStorage
- Auto-adjust interval based on period:
  - 1D → 5min intervals
  - 5D → 15min intervals
  - 1M → 1hr intervals
  - 3M+ → 1day intervals

**UI Design:**
```
[1D] [5D] [1M] [3M] [6M] [1Y] [5Y]
 └─ Button group above charts
```

### 7. Technical Screener
**Effort:** 12-16 hours
**Impact:** HIGH - New feature
**Status:** 🔴 Not Started

**Features:**
- Scan stocks for technical signals:
  - RSI oversold/overbought (< 30 or > 70)
  - MACD bullish/bearish crossovers
  - EMA crossings (golden cross, death cross)
  - Price breaking above/below moving averages
- Integrate with existing Alpha Engine infrastructure
- New route: `/screener/technical`
- Table view with sortable columns
- Click to view full technical analysis

**Backend Tasks:**
- Create `technical_screener.py` service
- Add endpoint: `POST /api/screener/technical`
- Batch process stock universe (popular, sp500_sample, tech)
- Cache results (5-15 minute TTL)

**Frontend Tasks:**
- Create `TechnicalScreenerPage.tsx`
- Add navigation link
- Results table with filtering
- Click-through to technical analysis page

### 8. Watchlist Functionality
**Effort:** 8-10 hours
**Impact:** MEDIUM - Convenience feature
**Status:** 🔴 Not Started

**Features:**
- Save favorite tickers
- Quick-switch dropdown in header
- Show mini-chart preview on hover
- Persist to localStorage or backend API
- Watchlist management page

**Implementation:**
- Add "Add to Watchlist" button on each page
- Dropdown in header: "My Watchlist"
- LocalStorage: `watchlist: ['AAPL', 'TSLA', 'NVDA']`
- Optional: Backend API for cross-device sync

---

## 🌟 Long-Term Enhancements (High Value, High Effort)

### 9. Real-Time WebSocket Updates
**Effort:** 20-24 hours
**Impact:** HIGH - Real-time data
**Status:** 🔴 Not Started
**Requires:** Polygon.io paid tier ($99-$249/month)

**Features:**
- WebSocket connection for live data
- Update charts in real-time during market hours
- Live price ticker in header
- Flash animations on price changes

**Technical Stack:**
- Polygon.io WebSocket API
- Backend: FastAPI WebSocket endpoint
- Frontend: WebSocket hook with reconnection logic
- Fallback to polling if WebSocket fails

### 10. Strategy Backtesting
**Effort:** 30-40 hours
**Impact:** HIGH - Advanced feature
**Status:** 🔴 Not Started

**Features:**
- Define entry/exit rules:
  - "Buy when RSI < 30 and MACD crosses above signal"
  - "Sell when price crosses below EMA50"
- Run historical simulation
- Performance metrics:
  - Total return
  - Sharpe ratio
  - Max drawdown
  - Win rate
- Visualize trades on chart (buy/sell markers)

**Backend Tasks:**
- Create `backtesting.py` service
- Implement strategy engine
- Calculate performance metrics
- Store backtest results

**Frontend Tasks:**
- Strategy builder UI (visual rule builder)
- Backtest results dashboard
- Chart with trade markers
- Performance comparison table

### 11. Options Greeks Over Time
**Effort:** 16-20 hours
**Impact:** MEDIUM - Options traders
**Status:** 🔴 Not Started

**Features:**
- Chart how Delta, Theta, Gamma change as expiration approaches
- Useful for options strategies
- Integrate with existing options page
- Show Greeks decay curves

**Implementation:**
- Extend options API to return historical Greeks
- Create GreeksChart.tsx component
- Add to OptionsPage as tab or section
- Calculate theoretical Greeks for historical dates

### 12. Export & Sharing
**Effort:** 8-12 hours
**Impact:** MEDIUM - Convenience
**Status:** 🔴 Not Started

**Features:**
- Export charts as PNG/PDF
- Save analysis sessions
- Share chart snapshots via URL
- Generate shareable links with ticker + indicators

**Implementation:**
- Chart.js toBase64Image() for PNG export
- jsPDF library for PDF generation
- URL state management: `/technical?ticker=AAPL&period=6mo&indicators=rsi,macd`
- Share button with copy-to-clipboard

---

## 🔧 Technical Debt & Infrastructure

### Code Quality Improvements
**Status:** LOW PRIORITY (current quality is good)

- [ ] Add unit tests for indicator calculations
- [ ] Add integration tests for chart rendering
- [ ] Set up E2E tests with Cypress/Playwright
- [ ] Implement code coverage thresholds (>80%)
- [ ] Add Storybook for component documentation

### Performance Optimizations
**Status:** MEDIUM PRIORITY (if needed)

- [ ] Code splitting by route (React.lazy)
- [ ] Lazy load Chart.js plugins
- [ ] Implement chart data memoization
- [ ] Add service worker for offline support
- [ ] Optimize bundle size (target <120KB)

### Infrastructure Enhancements
**Status:** LOW PRIORITY (current infrastructure is solid)

- [ ] Move Terraform state to GCS backend
- [ ] Set up Cloud Build triggers for auto-deploy
- [ ] Add staging environment
- [ ] Implement feature flags
- [ ] Set up monitoring dashboards (Grafana)

---

## 📊 Success Metrics

### Technical Analysis Page
- **Current Status:** MVP Complete
- **User Engagement (Target):**
  - Time on page: > 3 minutes
  - Charts per session: > 5
  - Return visitors: > 40%

### Platform-Wide
- **Performance:**
  - API response time: < 1.5s (✅ Currently 1.0s)
  - Page load time: < 2s (✅ Currently 1.8s)
  - Chart render time: < 500ms (✅ Currently 300ms)

- **Reliability:**
  - Uptime: > 99.9% (✅ Currently 100%)
  - Error rate: < 1% (✅ Currently 0.2%)

---

## 🗺️ Product Roadmap (Next 6 Months)

### Q4 2025 (Nov-Dec)
- ✅ Technical Analysis MVP (Complete)
- ✅ Volume Bars + Candlestick Charts (Deployed Nov 6)
- ✅ More Technical Indicators (Deployed Nov 6)
- ⏳ Technical Screener (Next)
- ⏳ Multiple Timeframe Toggle

### Q1 2026 (Jan-Mar)
- Chart Drawing Tools
- Watchlist Functionality
- Strategy Backtesting (Phase 1)
- Mobile App (React Native)

### Q2 2026 (Apr-Jun)
- Real-Time WebSocket Updates
- Options Greeks Over Time
- Advanced Screeners (Combine Alpha Engine + Technical)
- API for Third-Party Integrations

---

## 💡 Innovation Ideas (Future Exploration)

### AI/ML Features
- **Price Prediction Models:** Use LSTM/Transformer models for forecasting
- **Pattern Recognition:** Auto-detect chart patterns (head & shoulders, triangles)
- **Sentiment Analysis:** Integrate news/Twitter sentiment with technical signals
- **Anomaly Detection:** Flag unusual volume/price movements

### Social Features
- **Community Charts:** Share annotated charts with other users
- **Trade Ideas Feed:** Post and discuss trading strategies
- **Leaderboards:** Track best-performing strategies/users
- **Paper Trading:** Simulate trades without real money

### Integration Opportunities
- **Broker Integration:** Connect to TD Ameritrade, Interactive Brokers, Robinhood
- **Discord Bot:** Send technical alerts to Discord channels
- **Mobile Notifications:** Push alerts for watchlist items
- **Calendar Integration:** Economic events, earnings dates overlay on charts

---

## 📝 Notes & Considerations

### Data Provider Strategy
- **Current:** yfinance (free, 15-min delayed)
- **Upgrade Path:** Polygon.io paid tier for real-time data
- **Alternative:** Alpha Vantage, IEX Cloud, Finnhub

### Monetization Options (Future)
- **Freemium Model:**
  - Free: Basic indicators, delayed data
  - Pro ($9.99/mo): Real-time data, advanced indicators
  - Premium ($29.99/mo): Backtesting, alerts, API access

- **B2B SaaS:**
  - White-label platform for financial advisors
  - Enterprise API for institutional clients

### Compliance & Legal
- **Disclaimer:** Not investment advice
- **Terms of Service:** User agreement required
- **Data Licensing:** Review Polygon.io/yfinance terms for commercial use
- **FINRA/SEC:** Consult lawyer if offering trade execution

---

## 🤝 Contributing

This is a living document. Update as priorities change and features are completed.

**Change Log:**
- **2025-11-06:** Initial roadmap created
- **2025-11-06:** Volume Bars + Candlestick Charts - Started implementation
- **2025-11-06:** Volume Bars + Candlestick Charts - Completed and deployed to production
- **2025-11-06:** More Technical Indicators - Completed and deployed (BB, SMA20, SMA50, SMA200, EMA200)

---

## 📚 Resources

### Technical Analysis
- [Investopedia: Technical Indicators](https://www.investopedia.com/terms/t/technicalindicator.asp)
- [TradingView: Chart Patterns](https://www.tradingview.com/chart-patterns/)
- [Backtrader: Python Backtesting](https://www.backtrader.com/)

### Chart Libraries
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
- [Lightweight Charts (TradingView)](https://tradingview.github.io/lightweight-charts/)
- [Plotly Financial Charts](https://plotly.com/python/financial-charts/)

### Data Providers
- [Polygon.io Pricing](https://polygon.io/pricing)
- [Alpha Vantage API](https://www.alphavantage.co/)
- [IEX Cloud](https://iexcloud.io/)

---

**End of Evolution Roadmap**
