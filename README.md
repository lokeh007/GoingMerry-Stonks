# GoingMerry-Stonks

**Professional Stock and Options Analysis Platform**

A production-ready, cloud-native fintech application for analyzing stocks, options strategies, and discovering investment opportunities through sophisticated screening algorithms. Deployed on Google Cloud Platform with enterprise-grade infrastructure, security, and scalability.

[![Production](https://img.shields.io/badge/status-production-green)](https://api.goingmerry-stonks.com)
[![Infrastructure](https://img.shields.io/badge/infrastructure-terraform-purple)](terraform/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue)](.github/workflows/)
[![Coverage](https://img.shields.io/badge/coverage-54%25-yellow)](TESTING.md)

---

## 🎯 Overview

GoingMerry-Stonks is a modern financial analysis platform designed for serious traders and investors. It combines real-time market data, advanced options analysis, and proven investment screening strategies to help identify opportunities and understand risk.

**🌐 Live Application**: https://goingmerry-stonks.web.app
**📚 API Documentation**: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs

---

## 🎉 Recent Updates (November 2025)

### 🚀 Batch Screener System - Production Ready!
- ✅ **6,000 Stocks Screened Daily** - Full NYSE + NASDAQ coverage (up from 109 stocks!)
- ✅ **3 Batched Cloud Run Jobs** - Staggered execution to prevent API conflicts
  - Batch 1: 4:30 PM ET (A-H, ~2,000 stocks)
  - Batch 2: 6:00 PM ET (I-P, ~2,000 stocks)
  - Batch 3: 7:30 PM ET (Q-Z, ~2,000 stocks)
- ✅ **Firestore Cache Integration** - Results load instantly (<1 second vs 30-40 seconds)
- ✅ **Automated Daily Execution** - Fresh screener data every weekday evening
- ✅ **100% Free Data Sources** - SEC EDGAR + NASDAQ FTP (no paid API required)
- ✅ **Smart Money, Undiscovered, Coiled Spring** - All screeners cached for instant access

### Enhanced Stock Screener
- ✅ **yfinance Migration Complete** - Unlimited free market data, no more rate limits!
- ✅ **14 Financial Metrics** - Added PE ratio, revenue growth, 52-week high/low
- ✅ **Advanced Multi-Layer Screening** - Fundamentals + Technical + Market Context
- ✅ **6 Lynch Categories** - Complete Peter Lynch investment framework
- ✅ **Input Validation** - Type-safe stock universe selection with enums
- ✅ **Optimized Performance** - Debug-level logging for high-volume screening

### Technical Analysis Improvements
- ✅ **Gann Square of 9 Calculator** - Fixed None handling for stocks far from reference price
- ✅ **Support for All Stocks** - Works reliably for both low and high-priced stocks

### Code Quality Improvements
- ✅ **All Tests Passing** - 46/46 tests, 54% coverage
- ✅ **Simplified Codebase** - Removed dead code and unnecessary complexity
- ✅ **Better Configuration** - Environment variable support for technical limits
- ✅ **Improved Documentation** - Updated endpoint docs to match actual behavior
- ✅ **Enhanced Error Handling** - Proper exception handling for yfinance integration

---

## ✨ Key Features

### 📊 Options Analysis
- **Real-time option chain data** from Polygon.io
- **Interactive options grid** (strikes × expirations)
- **Black-Scholes-Merton pricing** and Greeks (Delta, Theta, Gamma, Vega, Rho)
- **Multiple strategies**: Long/Short Calls and Puts, Spreads
- **Smart defaults**: Shows 10 strikes around current price for focused analysis

### 📈 Technical Analysis (NEW!)
- **Interactive price charts** with line and candlestick views
- **Volume bars** with color-coded up/down days
- **10 Technical indicators** with toggle controls:
  - **Moving Averages**: EMA 12/26/50/200, SMA 20/50/200
  - **Momentum**: RSI (Relative Strength Index)
  - **Trend**: MACD (Moving Average Convergence Divergence)
  - **Volatility**: Bollinger Bands (upper/middle/lower)
- **Multi-timeframe analysis**: 1M to 5Y historical data
- **Professional charting** with Chart.js visualizations

### 📉 Profit/Loss Visualization
- **Interactive P/L charts** showing "hockey stick" diagrams
- **Automatic breakeven detection**
- **Risk/reward analysis** with ROC calculations
- **Hover tooltips** for precise P/L at any price point

### 🔍 Alpha Engine - Stock Screener (Production Grade!)
- **6,000 Stocks Daily**: Full NYSE + NASDAQ universe screened automatically
- **Instant Results**: Firestore cache delivers results in <1 second (vs 30-40 sec real-time)
- **3 Specialized Screeners**:
  - **Smart Money** - Unusual options activity, institutional positioning
  - **The Undiscovered** - Low institutional ownership + insider buying (Peter Lynch "tenbaggers")
  - **Coiled Spring** - NR7 volatility patterns (Bulkowski breakout setups)
- **6 Lynch Categories**: Fast Growers, Stalwarts, Slow Growers, Cyclicals, Turnarounds, Asset Plays
- **Advanced Multi-Layered Screening**:
  - **Layer 1: Fundamentals** - PEG ratio, earnings growth, debt ratios, ROE, liquidity
  - **Layer 2: Technical Triggers** - RSI, MACD, Gann levels, chart patterns
  - **Layer 3: Market Context** - VIX-based market regime filtering
- **Free Market Data**: Powered by yfinance + SEC EDGAR (unlimited, no paid APIs!)
- **14 Financial Metrics**: PE ratio, PEG, EPS growth, revenue growth, debt/equity, ROE, current ratio, institutional ownership, 52-week high/low, and more
- **Smart Scoring Algorithm**: 0-100 scoring based on multiple criteria
- **Customizable Criteria**: Adjust thresholds for PEG, growth rates, debt levels, etc.
- **Automated Daily Updates**: Runs Mon-Fri evenings, results ready before next trading day
- **Historical Tracking**: 30 days of cached results for trend analysis

### 🎯 Financial Metrics
- Net credit/debit calculations
- Maximum profit and loss analysis
- Breakeven price points
- Collateral requirements
- Return on capital (ROC)
- Risk/reward ratios

---

## 🏗️ Architecture

### Production Deployment (GCP)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet / Users                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │  Firebase Hosting    │
                    │  goingmerry-stonks   │
                    │  .web.app            │
                    │  Global CDN          │
                    └───────────┬───────────┘
                                │
                                ↓
                    ┌──────────────────────┐
                    │  Backend API         │
                    │  Cloud Run           │
                    │  FastAPI             │
                    │  /api/*, /options/*  │
                    │  /technical/*        │
                    │  /screener/*, /health│
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ↓              ↓              ↓
        ┌──────────────┐ ┌────────────┐ ┌──────────┐
        │   Cloud SQL   │ │  Secrets   │ │ Polygon  │
        │  PostgreSQL   │ │  Manager   │ │   API    │
        │  HA Enabled   │ │  API Keys  │ │  Market  │
        └──────────────┘ └────────────┘ └──────────┘
```

### Infrastructure Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React 18 + TypeScript | SPA with options & technical analysis UI |
| **Static Hosting** | Firebase Hosting | Frontend static assets with global CDN |
| **Backend API** | FastAPI + Python 3.11 | RESTful API for market data |
| **Application Runtime** | Cloud Run | Serverless container deployment |
| **Database** | Cloud SQL PostgreSQL 15 | Persistent data storage (HA enabled) |
| **Security** | Cloud Armor | DDoS protection, rate limiting, geo-blocking |
| **Secrets** | Secret Manager | API keys and credentials |
| **Monitoring** | Cloud Monitoring | Alerts for errors, latency, database |
| **Logging** | Cloud Logging | Centralized log aggregation |
| **IaC** | Terraform | Infrastructure as Code |
| **CI/CD** | GitHub Actions + Firebase Deploy | Automated testing and deployment |

---

## 🚀 Tech Stack

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Pydantic** - Data validation using Python type hints
- **yfinance** - Free, unlimited market data and fundamentals (NEW!)
- **Polygon.io API** - Real-time options data and historical prices
- **NumPy/SciPy** - Financial calculations and Black-Scholes model
- **SQLAlchemy** - Database ORM (future use)
- **Python 3.11** - Type hints, modern syntax

### Frontend
- **React 18** - Component-based UI library
- **TypeScript** - Static typing for JavaScript
- **Chart.js** - Data visualization for P/L charts
- **Axios** - HTTP client for API communication
- **CSS Grid/Flexbox** - Responsive layouts

### Infrastructure & DevOps
- **Terraform** - Infrastructure as Code
- **Docker** - Container packaging
- **Cloud Build** - Automated builds
- **GitHub Actions** - CI/CD workflows
- **pytest** - Python testing (46 tests, 54% coverage)
- **Black + Flake8 + MyPy** - Code quality tools
- **Bandit** - Security scanning

### Design Principles
- **SOLID Principles** - Clean, maintainable code architecture
- **KISS Principle** - Keep it simple and straightforward
- **RESTful API** - Standard HTTP methods and status codes
- **Type Safety** - Full-stack type coverage
- **Modular Design** - Separated concerns (routers, models, services, components)
- **Security by Default** - Least privilege, encrypted secrets, rate limiting

---

## 📁 Project Structure

```
GoingMerry-Stonks/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI application entry point
│   │   ├── models/
│   │   │   ├── options.py               # Option contract models
│   │   │   └── screener.py              # Stock screener models
│   │   ├── routers/
│   │   │   ├── options.py               # Options API endpoints
│   │   │   └── screener.py              # Screener API endpoints
│   │   ├── services/
│   │   │   ├── yfinance_provider.py     # yfinance market data integration (NEW!)
│   │   │   └── market_data.py           # Polygon.io integration (options)
│   │   └── financial_models/
│   │       └── options_pricing.py       # Black-Scholes-Merton model
│   ├── tests/                           # Test suite (46 tests)
│   ├── requirements.txt                 # Python dependencies
│   ├── Dockerfile                       # Multi-stage production build
│   └── .env                             # Environment variables (not in git)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── OptionsGrid.tsx          # Option chain table
│   │   │   ├── MetricsDisplay.tsx       # Financial metrics cards
│   │   │   ├── OptionsAnalyzer.tsx      # Main container component
│   │   │   └── ProfitLossChart.tsx      # P/L chart component
│   │   ├── utils/
│   │   │   ├── optionsDataTransform.ts  # Data transformation
│   │   │   ├── metricsCalculator.ts     # Financial calculations
│   │   │   └── profitLossCalculator.ts  # P/L calculations
│   │   ├── types/
│   │   │   ├── options.ts               # TypeScript interfaces
│   │   │   └── metrics.ts               # Metrics type definitions
│   │   └── styles/                      # Component CSS
│   ├── build/                           # Production build output
│   ├── package.json                     # Node dependencies
│   └── tsconfig.json                    # TypeScript configuration
│
├── terraform/
│   ├── environments/
│   │   └── prod/
│   │       ├── main.tf                  # Production infrastructure
│   │       ├── variables.tf             # Input variables
│   │       ├── outputs.tf               # Output values
│   │       └── terraform.tfvars         # Variable values (not in git)
│   └── modules/
│       ├── backend/                     # Cloud Run module
│       ├── database/                    # Cloud SQL module
│       ├── networking/                  # Load Balancer + CDN module
│       └── secrets/                     # Secret Manager module
│
├── .github/
│   └── workflows/
│       └── deploy.yml                   # GitHub Actions CI/CD
│
├── cloudbuild.yaml                      # Cloud Build configuration
├── firebase.json                        # Firebase Hosting config
├── README.md                            # This file
├── CLAUDE.md                            # Development guide for Claude Code
├── TESTING.md                           # Testing documentation
├── DEPLOYMENT_STATUS.md                 # Current deployment status
└── FRONTEND_DEPLOYMENT.md               # Frontend deployment details
```

---

## 🔧 Local Development

### Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **Docker** - Container runtime (optional)
- **Polygon.io API Key** - Market data ([free tier available](https://polygon.io/))

### Quick Start

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/GoingMerry-Stonks.git
cd GoingMerry-Stonks
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
echo "POLYGON_API_KEY=your_api_key_here" > .env

# Run tests
pytest --cov --cov-report=term-missing

# Start development server
uvicorn app.main:app --reload
# Server runs at: http://localhost:8000
# API docs at: http://localhost:8000/api/docs
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run tests
npm test

# Start development server
npm start
# Frontend runs at: http://localhost:3000
```

#### 4. Test the Integration

```bash
# Test API connectivity
python backend/test_api.py

# Test screener endpoints
python backend/test_screener.py

# Open browser
http://localhost:3000
```

---

## 🌐 Production Deployment

### Deployment Status

✅ **Infrastructure**: Fully deployed and operational
✅ **Backend API**: Running on Cloud Run (1-10 instances)
✅ **Database**: PostgreSQL HA with automatic backups
✅ **Load Balancer**: Global with Cloud Armor protection
✅ **Frontend**: Deployed to Firebase Hosting with global CDN
✅ **SSL Certificate**: Active (Google-managed)

### Production URLs

| Service | URL | Status |
|---------|-----|--------|
| **Frontend (Live)** | https://goingmerry-stonks.web.app | ✅ **LIVE** |
| **Frontend (Alt)** | https://goingmerry-stonks.firebaseapp.com | ✅ Active |
| **Backend API** | https://prod-backend-api-rlfl2vcoda-ul.a.run.app | ✅ Active (Public) |
| **API Docs** | https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs | ✅ Active |
| **Health Check** | https://prod-backend-api-rlfl2vcoda-ul.a.run.app/health | ✅ Active |

### Infrastructure Metrics

- **Test Coverage**: 54% (46/46 tests passing)
- **Uptime SLA**: 99.5% (Cloud Run)
- **Response Time**: P95 < 500ms
- **Database**: Regional HA with 7-day PITR
- **Backups**: Daily automated backups (30-day retention)
- **Security**: Cloud Armor rate limiting (100 req/min per IP)

### Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| Cloud Run (1-10 instances) | $25-100 |
| Cloud SQL (HA enabled) | $200-250 |
| Load Balancer + SSL | $18-25 |
| Cloud Storage + CDN | $1-5 |
| VPC Connector | $20 |
| Secrets + Monitoring | $1 |
| **Total** | **$265-401/month** |

---

## 📚 API Documentation

### Base URLs

- **Production**: https://api.goingmerry-stonks.com
- **Development**: http://localhost:8000

### Interactive Docs

- **Swagger UI**: `/api/docs`
- **ReDoc**: `/api/redoc`

### Key Endpoints

#### Health Check
```http
GET /health
```

#### Options Chain
```http
GET /options/{ticker}?expiration_date=2025-01-17&limit=50

Example: GET /options/AAPL?limit=100
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
```http
GET /screener/lynch-fast-growers?min_earnings_growth=15&max_peg_ratio=2.0&limit=20
```

**Parameters:**
- `min_earnings_growth` (float) - Minimum earnings growth rate (%)
- `max_peg_ratio` (float) - Maximum PEG ratio
- `min_current_ratio` (float) - Minimum current ratio
- `max_debt_to_equity` (float) - Maximum debt-to-equity ratio
- `min_market_cap` (float) - Minimum market cap (billions)
- `limit` (int) - Maximum results

---

## 🧪 Testing

### Backend Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=term-missing --cov-fail-under=54

# Run specific test file
pytest tests/test_screener.py

# Run with verbose output
pytest -v

# Quality checks
black app/ tests/              # Code formatting
flake8 app/ tests/             # Linting
mypy app/                      # Type checking
bandit -r app/                 # Security scanning
```

**Test Suite**: 46 tests, 54% coverage
- Unit tests: 44 passing
- Security tests: 3 passing
- Integration tests: 2 skipped (require production API key)

### Frontend Testing

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Build production bundle
npm run build
```

### CI/CD Testing

Tests run automatically on:
- Every push to `main` branch
- Every pull request
- Manual workflow dispatch

**Quality Gates**:
- ✅ All tests must pass
- ✅ Coverage ≥ 54%
- ✅ Black formatting check
- ✅ Flake8 linting check
- ✅ MyPy type checking
- ✅ Bandit security scan

---

## 🚢 Deployment

### Infrastructure as Code (Terraform)

All infrastructure is managed through Terraform:

```bash
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure (use with caution!)
terraform destroy
```

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/deploy.yml`):
1. ✅ Checkout code
2. ✅ Run backend tests
3. ✅ Build Docker image
4. ✅ Push to Artifact Registry
5. ✅ Deploy to Cloud Run
6. ✅ Build frontend
7. ✅ Deploy to Cloud Storage

**Cloud Build** (`cloudbuild.yaml`):
- Triggered on git push
- Runs test suite in container
- Builds multi-stage Docker image
- Deploys to Cloud Run

### Manual Deployment

```bash
# Backend deployment
cd backend
docker build -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 .
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0

gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 \
  --region=us-east5

# Frontend deployment
cd frontend
npm run build
gsutil -m rsync -r -d build gs://sylvan-earth-477020-u6-frontend
```

---

## 🔒 Security

### Implemented Security Measures

- ✅ **Cloud Armor**: DDoS protection, rate limiting (100 req/min per IP)
- ✅ **Geo-blocking**: Russia blocked at edge
- ✅ **SQL Injection Protection**: Preconfigured WAF rules
- ✅ **XSS Protection**: Preconfigured WAF rules
- ✅ **Secret Management**: All credentials in Secret Manager
- ✅ **Least Privilege IAM**: Service accounts with minimal permissions
- ✅ **Network Isolation**: Private VPC for database
- ✅ **Encrypted Secrets**: AES-256 encryption at rest
- ✅ **SSL/TLS**: Managed certificates with auto-renewal
- ✅ **HTTPS Only**: HTTP → HTTPS redirect
- ✅ **Security Headers**: X-Frame-Options, CSP, etc.
- ✅ **Container Scanning**: Automated vulnerability scanning

### Security Best Practices

1. **Never commit sensitive data**:
   - `.env` files
   - `terraform.tfvars` files
   - API keys or passwords

2. **Use Secret Manager** for all credentials:
   ```bash
   gcloud secrets create my-secret --data-file=secret.txt
   ```

3. **Follow principle of least privilege**:
   - Service accounts have minimal required permissions
   - Cloud Run ingress: Load Balancer only

4. **Enable audit logging**:
   - All API calls logged
   - Database connections monitored

---

## 📊 Monitoring & Observability

### Cloud Monitoring Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| High Error Rate | >5% 5xx errors | Email notification |
| High Latency | P95 >2 seconds | Email notification |
| Database Connections | >80% of max | Email notification |

### Logging

- **Cloud Logging**: 100% sample rate
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Retention**: 30 days (configurable)

### Metrics

- Request count and error rate
- Latency (P50, P95, P99)
- Database connection pool utilization
- CPU and memory usage
- Network egress

---

## 🗺️ Roadmap

### ✅ Phase 1: Foundation (Complete)
- [x] FastAPI backend structure
- [x] Polygon.io API integration
- [x] Options chain endpoint
- [x] React frontend components
- [x] P/L chart visualization
- [x] Lynch Fast Growers screener
- [x] Production infrastructure on GCP
- [x] CI/CD pipelines
- [x] Test coverage ≥54%

### 🔄 Phase 2: Production Hardening (In Progress)
- [x] Cloud Storage frontend deployment
- [ ] DNS configuration for custom domain
- [ ] SSL certificate activation
- [ ] Performance optimization
- [ ] Error monitoring and alerting
- [ ] Database migrations
- [ ] Increase test coverage to 70%+

### 📋 Phase 3: Enhanced Analysis
- [ ] Real-time market data integration
- [ ] Additional screeners (Value, Dividend, Momentum)
- [ ] Spread strategies (Bull Call, Bear Put, Iron Condor)
- [ ] Historical backtesting
- [ ] Portfolio analysis
- [ ] WebSocket for real-time updates

### 📋 Phase 4: Advanced Features
- [ ] User authentication (Firebase Auth)
- [ ] User portfolios and watchlists
- [ ] Alert system for screening matches
- [ ] Custom screener builder
- [ ] Trade journaling
- [ ] Performance tracking
- [ ] Mobile app (React Native)

---

## 📖 Documentation

### Main Documentation
- **[README.md](README.md)** - This file
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **[TESTING.md](TESTING.md)** - Testing infrastructure and procedures
- **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** - Infrastructure deployment status
- **[FIREBASE_DEPLOYMENT.md](FIREBASE_DEPLOYMENT.md)** - Firebase Hosting deployment (ACTIVE)
- **[FRONTEND_DEPLOYMENT.md](FRONTEND_DEPLOYMENT.md)** - Cloud Storage deployment (alternative)

### Specialized Guides
- **[backend/ALPHA_ENGINE_GUIDE.md](backend/ALPHA_ENGINE_GUIDE.md)** - Stock screener documentation
- **[frontend/COMPONENTS.md](frontend/COMPONENTS.md)** - Component API reference
- **[frontend/INTEGRATION_GUIDE.md](frontend/INTEGRATION_GUIDE.md)** - Integration patterns
- **[frontend/PROFIT_LOSS_CHART_GUIDE.md](frontend/PROFIT_LOSS_CHART_GUIDE.md)** - P/L chart usage

### API Documentation
- **Swagger UI**: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs
- **ReDoc**: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/redoc

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow code style**:
   - Backend: PEP 8, type hints, docstrings
   - Frontend: ESLint, Prettier, TypeScript
4. **Write tests** for new features (maintain ≥54% coverage)
5. **Update documentation** as needed
6. **Run quality checks**:
   ```bash
   # Backend
   black app/ tests/
   flake8 app/ tests/
   mypy app/
   pytest --cov

   # Frontend
   npm test
   npm run build
   ```
7. **Commit changes**: `git commit -m 'Add amazing feature'`
8. **Push to branch**: `git push origin feature/amazing-feature`
9. **Open a Pull Request**

---

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check .env file
cat backend/.env
```

**Frontend build errors:**
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install --force

# TypeScript errors
npm run build
```

**API connection errors:**
```bash
# Test Polygon.io API
python backend/test_api.py

# Check logs
gcloud run services logs read prod-backend-api --region=us-east5
```

**Production deployment issues:**
```bash
# Check Cloud Run status
gcloud run services describe prod-backend-api --region=us-east5

# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check database
gcloud sql instances describe prod-postgres-d05b2fe9
```

See **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** for complete troubleshooting guide.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **Peter Lynch** - Fast Growers investment strategy and six stock categories
- **Black, Scholes, Merton** - Options pricing model
- **yfinance** - Free market data and fundamentals API
- **Polygon.io** - Real-time options and market data API
- **FastAPI** - Modern Python web framework
- **React & TypeScript** - Frontend framework and type safety
- **React** - UI component library
- **Chart.js** - Data visualization
- **Google Cloud Platform** - Cloud infrastructure
- **Terraform** - Infrastructure as Code

---

## 📞 Contact & Support

**Project Repository**: https://github.com/yourusername/GoingMerry-Stonks

**Production Status**: See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for current status

**Issue Tracker**: https://github.com/yourusername/GoingMerry-Stonks/issues

---

**Built with passion for financial markets and clean code** 📊🚀

*GoingMerry-Stonks - Sail towards financial freedom with data-driven insights*

---

## 📈 Project Status

| Metric | Value |
|--------|-------|
| Backend Tests | 46/46 passing ✅ |
| Test Coverage | 54% ✅ |
| Production Status | **LIVE** ✅ |
| Frontend URL | https://goingmerry-stonks.web.app ✅ |
| Frontend Build | 146 KB gzipped ✅ |
| API Latency (P95) | <500ms ✅ |
| Database HA | Enabled ✅ |
| SSL Certificate | Active (Google-managed) ✅ |
| Global CDN | Active (Firebase) ✅ |

### 🆕 Recent Updates (November 6, 2025)

**Technical Analysis Platform Complete! 📊**
- ✅ Added **Volume Bars** with color-coded up/down days
- ✅ Added **Candlestick Charts** with toggle between line/candlestick views
- ✅ Implemented **10 Technical Indicators**:
  - Bollinger Bands (upper, middle, lower)
  - SMA 20, 50, 200
  - EMA 12, 26, 50, 200
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
- ✅ Added **indicator toggle controls** - check/uncheck any combination
- ✅ **Options page improvements**: Default shows 10 strikes (focused analysis)
- ✅ **Multi-timeframe support**: 1M, 3M, 6M, 1Y, 2Y, 5Y historical data
- ✅ **Chart type toggle**: Switch between line and candlestick views
- ✅ **Professional UI**: Dark theme with color-coded indicators

**Next Up**: Technical Screener, Multiple Timeframe Toggle, Chart Drawing Tools

---

Last Updated: November 6, 2025
**Status**: Production-ready and serving users worldwide 🌐
