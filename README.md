# GoingMerry-Stonks

**Professional Stock and Options Analysis Platform**

A comprehensive full-stack fintech application for analyzing stocks, options strategies, and discovering investment opportunities through sophisticated screening algorithms.

---

## Overview

GoingMerry-Stonks is a modern financial analysis platform designed for serious traders and investors. It combines real-time market data, advanced options analysis, and proven investment screening strategies to help identify opportunities and understand risk.

### Key Features

📊 **Options Analysis**
- Real-time option chain data from Polygon.io
- Interactive options grid (strikes × expirations)
- Black-Scholes-Merton pricing and Greeks (Delta, Theta, Gamma, Vega, Rho)
- Multiple strategies: Long/Short Calls and Puts, Spreads

📈 **Profit/Loss Visualization**
- Interactive P/L charts showing "hockey stick" diagrams
- Automatic breakeven detection
- Risk/reward analysis with ROC calculations
- Hover tooltips for precise P/L at any price point

🔍 **Alpha Engine - Stock Screener**
- Lynch Fast Growers: Peter Lynch's growth investing strategy
- Customizable screening criteria
- Detailed financial metrics (PEG ratio, earnings growth, financial health)
- Scored and ranked results with reasoning

🎯 **Financial Metrics**
- Net credit/debit calculations
- Maximum profit and loss analysis
- Breakeven price points
- Collateral requirements
- Return on capital (ROC)
- Risk/reward ratios

---

## Tech Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Pydantic** - Data validation using Python type hints
- **Polygon.io API** - Real-time and historical market data
- **NumPy/SciPy** - Financial calculations and Black-Scholes model
- **Python 3.10+** - Type hints, modern syntax

### Frontend
- **React 18** - Component-based UI library
- **TypeScript** - Static typing for JavaScript
- **Chart.js** - Data visualization for P/L charts
- **Axios** - HTTP client for API communication
- **CSS Grid/Flexbox** - Responsive layouts

### Architecture
- **SOLID Principles** - Clean, maintainable code architecture
- **KISS Principle** - Keep it simple and straightforward
- **RESTful API** - Standard HTTP methods and status codes
- **Type Safety** - Full-stack type coverage
- **Modular Design** - Separated concerns (routers, models, services, components)

---

## Project Structure

```
GoingMerry-Stonks/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── models/
│   │   │   ├── options.py           # Option contract models
│   │   │   └── screener.py          # Stock screener models
│   │   ├── routers/
│   │   │   ├── options.py           # Options API endpoints
│   │   │   └── screener.py          # Screener API endpoints
│   │   ├── services/
│   │   │   └── market_data.py       # Polygon.io integration
│   │   └── financial_models/
│   │       └── options_pricing.py   # Black-Scholes-Merton model
│   ├── requirements.txt             # Python dependencies
│   ├── test_api.py                  # API connection test
│   ├── test_screener.py             # Screener endpoint tests
│   ├── .env                         # Environment variables (API keys)
│   └── ALPHA_ENGINE_GUIDE.md        # Alpha Engine documentation
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── OptionsGrid.tsx      # Option chain table
│   │   │   ├── MetricsDisplay.tsx   # Financial metrics cards
│   │   │   ├── OptionsAnalyzer.tsx  # Main container component
│   │   │   ├── ProfitLossChart.tsx  # P/L chart component
│   │   │   └── PLChartExample.tsx   # Interactive P/L demo
│   │   ├── utils/
│   │   │   ├── optionsDataTransform.ts    # Data transformation
│   │   │   ├── metricsCalculator.ts       # Financial calculations
│   │   │   └── profitLossCalculator.ts    # P/L calculations
│   │   ├── types/
│   │   │   ├── options.ts           # TypeScript interfaces
│   │   │   └── metrics.ts           # Metrics type definitions
│   │   └── styles/
│   │       ├── OptionsGrid.css
│   │       ├── MetricsDisplay.css
│   │       ├── OptionsAnalyzer.css
│   │       └── ProfitLossChart.css
│   ├── package.json                 # Node dependencies
│   ├── tsconfig.json                # TypeScript configuration
│   ├── COMPONENTS.md                # Component documentation
│   ├── INTEGRATION_GUIDE.md         # Integration instructions
│   └── PROFIT_LOSS_CHART_GUIDE.md   # P/L chart guide
│
└── README.md                        # This file
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** - Backend runtime
- **Node.js 16+** - Frontend runtime
- **Polygon.io API Key** - Market data (free tier available)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/GoingMerry-Stonks.git
cd GoingMerry-Stonks
```

#### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your Polygon.io API key:
# POLYGON_API_KEY=your_api_key_here
```

#### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Or with yarn:
yarn install
```

### Running the Application

#### Start Backend Server

```bash
cd backend
source venv/bin/activate  # Activate virtual environment

# Run with uvicorn
uvicorn app.main:app --reload

# Server will start at: http://localhost:8000
# API docs available at: http://localhost:8000/api/docs
```

#### Start Frontend Development Server

```bash
cd frontend

# With npm:
npm start

# Or with yarn:
yarn start

# Frontend will start at: http://localhost:3000
```

#### Test the API

```bash
# Test basic connection
python backend/test_api.py

# Test screener endpoints
python backend/test_screener.py
```

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive API Docs
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

#### Health Check
```bash
GET /health
```

#### Options Chain
```bash
GET /options/{ticker}?expiration_date=2025-01-17&limit=50

# Example:
GET /options/AAPL?limit=100
```

**Response:**
```json
{
  "ticker": "AAPL",
  "stock_price": 185.92,
  "total_contracts": 100,
  "calls": [...],
  "puts": [...]
}
```

#### Stock Screener - Lynch Fast Growers
```bash
GET /screener/lynch-fast-growers?min_earnings_growth=15&max_peg_ratio=2.0&limit=20
```

**Parameters:**
- `min_earnings_growth` (float, default: 10.0) - Minimum earnings growth rate (%)
- `max_peg_ratio` (float, default: 2.5) - Maximum PEG ratio
- `min_current_ratio` (float, default: 1.0) - Minimum current ratio
- `max_debt_to_equity` (float, default: 2.0) - Maximum debt-to-equity ratio
- `min_market_cap` (float, default: 1.0) - Minimum market cap (billions)
- `limit` (int, default: 20) - Maximum results

**Response:**
```json
{
  "screener_name": "Lynch Fast Growers",
  "description": "Peter Lynch's Fast Growers strategy...",
  "total_results": 8,
  "timestamp": "2025-01-17T10:30:00",
  "criteria": {...},
  "results": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "sector": "Technology",
      "score": 92.5,
      "peg_ratio": 1.8,
      "earnings_growth": 35.2,
      "reasons": ["Exceptional earnings growth (35.2%)", ...]
    }
  ]
}
```

#### List Available Screeners
```bash
GET /screener/screeners
```

---

## Usage Examples

### Options Analysis

```tsx
import { OptionsAnalyzer } from './components';

function App() {
  return (
    <OptionsAnalyzer
      optionChainData={optionData}
      defaultStrategy="short_put"
      onMetricsCalculated={(metrics) => {
        console.log('Calculated metrics:', metrics);
      }}
    />
  );
}
```

**Features:**
- Click any cell in options grid to calculate metrics
- Select strategy (Short Put, Long Call, Long Put, Short Call)
- View P/L chart automatically
- See breakeven points, max profit/loss, ROC

### Profit/Loss Chart

```tsx
import { ProfitLossChart } from './components';

function MyChart() {
  return (
    <ProfitLossChart
      strategyParams={{
        type: 'short_put',
        strike: 150,
        premium: 5.25,
        currentStockPrice: 155
      }}
      height={450}
      showBreakevens={true}
    />
  );
}
```

### Stock Screening (Python)

```python
import requests

# Screen for fast growers
response = requests.get(
    'http://localhost:8000/screener/lynch-fast-growers',
    params={
        'min_earnings_growth': 15.0,
        'max_peg_ratio': 2.0,
        'limit': 10
    }
)

results = response.json()

for stock in results['results']:
    print(f"{stock['ticker']}: Score {stock['score']}")
    print(f"  PEG: {stock['peg_ratio']}, Growth: {stock['earnings_growth']}%")
    print(f"  Reasons: {', '.join(stock['reasons'])}")
```

---

## Features in Detail

### 1. Options Analysis

The options module provides comprehensive analysis of option contracts:

**OptionsGrid Component**
- Displays option chain as interactive table
- Rows = strike prices, Columns = expiration dates
- Color coding: ITM (green), ATM (orange), OTM (white)
- Sticky headers for easy navigation
- Click cells to select and analyze

**MetricsDisplay Component**
- Net credit/debit position
- Maximum profit and loss
- Breakeven price points
- Collateral requirements
- Return on capital (ROC)
- Risk/reward ratios

**Supported Strategies:**
- Long Call - Bullish, unlimited upside
- Long Put - Bearish, limited risk
- Short Call - Bearish, collect premium
- Short Put - Bullish, cash-secured
- *(Future: Spreads, Iron Condors, Butterflies)*

### 2. Profit/Loss Visualization

Interactive P/L charts using Chart.js:

**Features:**
- Characteristic "hockey stick" shape
- Color-coded profit (green) and loss (red) zones
- Automatic breakeven point detection
- Hover tooltips showing exact P/L at any price
- Adjustable price range and data point density
- Information panel with strategy details

**Example:**
```
  Profit
    ↑
    |     ──────────────────  (Max profit: $525)
    |    /
    |   /
────|──/─────────────────────→ Stock Price
    | /  BE ($144.75)
    |/
    /    (Max loss increases as stock drops)
```

### 3. Alpha Engine - Stock Screener

Sophisticated stock screening based on proven investment strategies:

**Lynch Fast Growers Strategy**

Based on Peter Lynch's legendary Fidelity Magellan Fund approach:

- **Target:** Companies with 20-25% annual earnings growth
- **Valuation:** PEG ratio < 2.5 (ideally < 1.0)
- **Financial Health:** Strong balance sheet, manageable debt
- **Market Cap:** Focus on mid-cap to large-cap ($1B+)

**Scoring System (0-100):**
- Earnings Growth (35 points)
- PEG Ratio (30 points)
- Financial Health (20 points)
- Revenue Growth (15 points)

**Result Fields:**
- Ticker, company name, sector
- Price, market cap, PE ratio
- PEG ratio, earnings/revenue growth
- Debt-to-equity, current ratio
- Score and reasoning

**Coming Soon:**
- Value Screener (Benjamin Graham)
- Dividend Aristocrats
- Momentum Screener
- Quality Screener (Buffett-style)

### 4. Black-Scholes-Merton Model

Accurate options pricing using the BSM formula:

**Implemented Greeks:**
- **Delta** (Δ) - Price sensitivity to underlying
- **Theta** (Θ) - Time decay
- **Gamma** (Γ) - Delta sensitivity
- **Vega** (ν) - Volatility sensitivity
- **Rho** (ρ) - Interest rate sensitivity

**Usage:**
```python
from app.financial_models.options_pricing import calculate_bsm_price

price = calculate_bsm_price(
    S=155.0,      # Stock price
    K=150.0,      # Strike price
    T=0.25,       # Time to expiration (years)
    r=0.05,       # Risk-free rate
    sigma=0.30,   # Volatility
    option_type="call"
)
```

---

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Polygon.io API Configuration
POLYGON_API_KEY=your_api_key_here

# Optional: API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Data Cache Settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
```

### API Rate Limits

**Polygon.io Free Tier:**
- 5 API calls per minute
- Delayed data (15 minutes)

**Polygon.io Paid Tiers:**
- Higher rate limits
- Real-time data
- Historical data access

### CORS Configuration

The backend allows requests from `http://localhost:3000` by default. To modify:

```python
# backend/app/main.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourdomain.com"
    ],
    # ...
)
```

---

## Testing

### Backend Tests

```bash
# Test API connection
cd backend
python test_api.py

# Test screener endpoints
python test_screener.py

# Run unit tests (when available)
pytest
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

### Manual Testing

1. **Start the backend server**
2. **Visit API docs**: http://localhost:8000/api/docs
3. **Try the endpoints** using the interactive Swagger UI
4. **Start the frontend** and test UI interactions

---

## Documentation

- **Backend API**: http://localhost:8000/api/docs (Swagger UI)
- **Alpha Engine**: `backend/ALPHA_ENGINE_GUIDE.md`
- **Frontend Components**: `frontend/COMPONENTS.md`
- **Integration Guide**: `frontend/INTEGRATION_GUIDE.md`
- **P/L Chart Guide**: `frontend/PROFIT_LOSS_CHART_GUIDE.md`

---

## Roadmap

### Phase 1: Foundation ✅
- [x] FastAPI backend structure
- [x] Polygon.io API integration
- [x] Options chain endpoint
- [x] React frontend components
- [x] Options grid and metrics display
- [x] P/L chart visualization
- [x] Lynch Fast Growers screener

### Phase 2: Enhanced Analysis 🔄
- [ ] Real-time market data integration for screener
- [ ] Additional screeners (Value, Dividend, Momentum)
- [ ] Spread strategies (Bull Call, Bear Put, Iron Condor)
- [ ] Historical backtesting
- [ ] Portfolio analysis

### Phase 3: Advanced Features 📋
- [ ] User authentication and portfolios
- [ ] Alert system for screening matches
- [ ] Custom screener builder
- [ ] Trade journaling
- [ ] Performance tracking
- [ ] Mobile app

### Phase 4: Machine Learning 📋
- [ ] Predictive analytics
- [ ] Pattern recognition
- [ ] Risk scoring
- [ ] Sentiment analysis
- [ ] Automated strategy suggestions

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow code style**:
   - Backend: PEP 8, type hints, docstrings
   - Frontend: ESLint, Prettier, TypeScript
4. **Write tests** for new features
5. **Update documentation** as needed
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Style

**Python (Backend):**
```python
def calculate_metrics(
    strike: float,
    premium: float,
    stock_price: float,
) -> FinancialMetrics:
    """
    Calculate financial metrics for an option strategy.

    Args:
        strike: Strike price of the option
        premium: Premium paid or received
        stock_price: Current stock price

    Returns:
        FinancialMetrics object with calculated values
    """
    # Implementation
```

**TypeScript (Frontend):**
```typescript
interface StrategyParams {
  type: StrategyType;
  strike: number;
  premium: number;
  currentStockPrice?: number;
}

export const calculatePL = (params: StrategyParams): number => {
  // Implementation
};
```

---

## Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check for port conflicts
lsof -i :8000
```

**Frontend build errors:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear cache
npm cache clean --force
```

**API connection errors:**
```bash
# Verify .env file exists
cat backend/.env

# Test API key
python backend/test_api.py

# Check Polygon.io API status
curl https://api.polygon.io/v3/reference/tickers/AAPL?apiKey=YOUR_KEY
```

**CORS errors:**
- Ensure backend is running on port 8000
- Ensure frontend is running on port 3000
- Check CORS configuration in `backend/app/main.py`

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **Peter Lynch** - Fast Growers investment strategy
- **Black, Scholes, Merton** - Options pricing model
- **Polygon.io** - Market data API
- **FastAPI** - Modern Python web framework
- **React** - UI component library
- **Chart.js** - Data visualization

---

## Contact

**Project Link**: https://github.com/yourusername/GoingMerry-Stonks

**Built with passion for financial markets and clean code** 📊🚀

---

*GoingMerry-Stonks - Sail towards financial freedom with data-driven insights*
