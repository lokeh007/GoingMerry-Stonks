# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GoingMerry-Stonks is a **production-deployed** full-stack financial analysis platform for options trading and stock screening. The application consists of a FastAPI backend serving market data from Polygon.io and a React/TypeScript frontend for visualization and analysis.

**Production Status**: ✅ Deployed to Google Cloud Platform
**Environment**: Production (sylvan-earth-477020-u6)
**Region**: us-east5
**Live URLs**:
- **Frontend (PRIMARY)**: https://goingmerry-stonks.web.app (Firebase Hosting)
- Backend API: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs

---

## Production Architecture

### Current Deployment (November 2025)

```
Internet
    ├─ Frontend: Firebase Hosting (PRIMARY)
    │  └─ URL: https://goingmerry-stonks.web.app
    │  └─ Serves: React SPA (build/)
    │  └─ CDN: Global (Firebase CDN)
    │  └─ Cache: Loads screener results from Firestore (<1 sec)
    │
    ├─ Frontend (BACKUP): Cloud Storage + CDN
    │  └─ Bucket: gs://sylvan-earth-477020-u6-frontend
    │  └─ Note: Alternative deployment option
    │
    ├─ Backend: Cloud Run (FastAPI)
    │  ├─ URL: https://prod-backend-api-rlfl2vcoda-ul.a.run.app
    │  ├─ Routes: /api/*, /options/*, /screener/*, /technical/*, /health
    │  ├─ Database: Cloud SQL PostgreSQL 15 (HA enabled)
    │  ├─ Secrets: Secret Manager (Polygon API key, DB credentials)
    │  └─ Security: Cloud Armor (rate limiting, geo-blocking)
    │
    └─ Batch Screeners: Cloud Run Jobs (Automated Daily, Sequential)
       ├─ Regular Screeners (Undiscovered + Coiled Spring, 60 req/min):
       │  ├─ Batch 1: 4:30 PM ET → 6:00 PM (A to CURB, ~992 stocks)
       │  ├─ Batch 2: 6:00 PM ET → 7:30 PM (CURV to GRNJ, ~992 stocks)
       │  ├─ Batch 3: 7:30 PM ET → 9:00 PM (GRNT to MPU, ~992 stocks)
       │  ├─ Batch 4: 9:00 PM ET → 10:30 PM (MPV to SFGV, ~992 stocks)
       │  └─ Batch 5: 10:30 PM ET → 12:00 AM (SFL to ZWS, ~992 stocks)
       │
       ├─ Smart Money Screeners (Options Flow, 45 req/min):
       │  ├─ Batch 1: 12:00 AM ET → 2:00 AM (A-D, ~1200 stocks)
       │  ├─ Batch 2: 2:00 AM ET → 4:00 AM (E-J, ~1200 stocks)
       │  ├─ Batch 3: 4:00 AM ET → 6:00 AM (K-N, ~1200 stocks)
       │  ├─ Batch 4: 6:00 AM ET → 8:00 AM (O-S, ~1200 stocks)
       │  └─ Batch 5: 8:00 AM ET → 10:00 AM (T-Z, ~1200 stocks)
       │
       ├─ Coverage: ~6,000 NYSE + NASDAQ stocks total
       ├─ Schedulers: 10 Cloud Schedulers (Mon-Fri, zero overlap)
       ├─ Cache: Saves results to Firestore for instant frontend loading
       └─ Sources: Yahoo Finance (free, no API keys required)
```

### Infrastructure Components

| Component | Resource Name | Status |
|-----------|---------------|--------|
| **Frontend (PRIMARY)** | goingmerry-stonks (Firebase) | ✅ Active |
| **Backend Service** | prod-backend-api | ✅ Running (Cloud Run) |
| **Regular Screeners 1** | prod-regular-screeners-batch-1 | ✅ Active (A-D, 4:30 PM) |
| **Regular Screeners 2** | prod-regular-screeners-batch-2 | ✅ Active (E-J, 6:00 PM) |
| **Regular Screeners 3** | prod-regular-screeners-batch-3 | ✅ Active (K-N, 7:30 PM) |
| **Regular Screeners 4** | prod-regular-screeners-batch-4 | ✅ Active (O-S, 9:00 PM) |
| **Regular Screeners 5** | prod-regular-screeners-batch-5 | ✅ Active (T-Z, 10:30 PM) |
| **Smart Money 1** | prod-smart-money-screeners-batch-1 | ✅ Active (A-D, 12:00 AM) |
| **Smart Money 2** | prod-smart-money-screeners-batch-2 | ✅ Active (E-J, 2:00 AM) |
| **Smart Money 3** | prod-smart-money-screeners-batch-3 | ✅ Active (K-N, 4:00 AM) |
| **Smart Money 4** | prod-smart-money-screeners-batch-4 | ✅ Active (O-S, 6:00 AM) |
| **Smart Money 5** | prod-smart-money-screeners-batch-5 | ✅ Active (T-Z, 8:00 AM) |
| **Firestore Database** | (default) | ✅ Active (screener cache) |
| **Database** | prod-postgres-d05b2fe9 | ✅ RUNNABLE (PostgreSQL 15) |
| **Frontend (Backup)** | sylvan-earth-477020-u6-frontend | ✅ Active (Cloud Storage) |
| **VPC Connector** | prod-vpc-connector | ✅ Active |
| **Artifact Registry** | prod-backend | ✅ Active |

**Note**: 10 Cloud Schedulers trigger the jobs above (5 for regular, 5 for Smart Money).

### Deployment Method

- **Infrastructure**: Terraform (all resources defined in `terraform/`)
- **Backend**: Docker → Cloud Run (serverless containers)
- **Frontend (PRIMARY)**: npm build → Firebase Hosting (`firebase deploy --only hosting`)
- **Frontend (Backup)**: npm build → Cloud Storage (`gsutil rsync`)
- **CI/CD**: GitHub Actions + Cloud Build

**IMPORTANT**: Always deploy frontend to Firebase Hosting for production updates!

---

## Local Development Setup

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

# Run tests
pytest --cov --cov-report=term-missing --cov-fail-under=54

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

# Run tests
npm test

# Run development server
npm start
# Frontend runs at: http://localhost:3000

# Build for production
npm run build
# Output: frontend/build/ directory
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

# Full backend test suite (46 tests, 54% coverage)
cd backend
pytest --cov --cov-report=term-missing

# Frontend tests
cd frontend && npm test
```

---

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
  - `market_data.py` - **MarketDataProvider class**: Centralized Polygon.io API client
- **`app/financial_models/`** - Financial calculations
  - `options_pricing.py` - Black-Scholes-Merton pricing model and Greeks calculations
- **`tests/`** - Test suite (46 tests, 54% coverage)
  - Unit tests, security tests, integration tests
  - Quality gates: Black, Flake8, MyPy, Bandit

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
- **`build/`** - Production build output (135 KB main.js gzipped)

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

---

## Production Deployment

### Infrastructure as Code (Terraform)

All infrastructure is managed via Terraform in `terraform/environments/prod/`:

```bash
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply infrastructure changes
terraform apply

# View outputs (URLs, IPs, connection names)
terraform output
```

**Terraform Modules**:
- `modules/backend/` - Cloud Run service, service account, IAM
- `modules/database/` - Cloud SQL instance, database, user, secrets
- `modules/networking/` - Load balancer, CDN, SSL, Cloud Armor
- `modules/secrets/` - Secret Manager for Polygon API key

**State Management**: Local state file (consider migrating to GCS backend for team collaboration)

### CI/CD Pipelines

**GitHub Actions** (`.github/workflows/deploy.yml`):
1. Checkout code
2. Set up Python and run pytest
3. Build Docker image with multi-stage build
4. Push to Artifact Registry (us-east5-docker.pkg.dev)
5. Deploy to Cloud Run
6. Build frontend (npm run build)
7. Deploy to Firebase Hosting

**Note**: CI/CD pipeline should be updated to use `firebase deploy --only hosting` instead of Cloud Storage

**Cloud Build** (`cloudbuild.yaml`):
- Triggered on git push to main
- Runs test suite in containerized environment
- Builds production Docker image
- Deploys to Cloud Run automatically

**Quality Gates**:
- ✅ All 46 tests must pass
- ✅ Coverage ≥ 54%
- ✅ Black formatting check
- ✅ Flake8 linting (max-line-length=100)
- ✅ MyPy type checking
- ✅ Bandit security scan (no critical issues)

### Manual Deployment Commands

```bash
# Backend deployment
cd backend
docker build -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 .
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0

gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 \
  --region=us-east5

# Frontend deployment (PRIMARY METHOD - Firebase Hosting)
cd frontend
npm run build
firebase deploy --only hosting

# Frontend deployment (BACKUP METHOD - Cloud Storage)
cd frontend
npm run build
gsutil -m rsync -r -d build gs://sylvan-earth-477020-u6-frontend
```

**IMPORTANT - Frontend Deployment**:
- **PRIMARY**: Use Firebase Hosting (`firebase deploy --only hosting`)
  - Production URL: https://goingmerry-stonks.web.app
  - Instant deployment with global CDN
  - This is the URL users access!

- **BACKUP**: Cloud Storage is available but NOT the primary deployment target
  - Only use for testing or backup purposes
  - Not connected to the main domain

---

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

---

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

---

## Environment Configuration

### Backend `.env` File (required)

```bash
POLYGON_API_KEY=your_polygon_api_key_here
```

**Polygon.io API Notes**:
- Free tier: 5 calls/minute, 15-minute delayed data
- Options snapshots are rate-limited (limited to 50 contracts in `get_option_chain()`)
- Financials endpoint requires paid tier for real-time data

### Production Secrets (Secret Manager)

All production credentials are stored in Google Secret Manager:
- `prod-polygon-api-key` - Polygon.io API key
- `prod-db-password` - PostgreSQL database password
- `prod-database-url` - Full database connection string

Backend service account has `secretmanager.secretAccessor` role for these secrets.

### Frontend Environment Variables

**Development** (`frontend/.env.development`):
```bash
REACT_APP_API_URL=http://localhost:8000
```

**Production** (`frontend/.env.production`):
```bash
REACT_APP_API_URL=/api
NODE_ENV=production
GENERATE_SOURCEMAP=false
```

Production uses relative URLs (`/api/*`) which are routed by the load balancer to the backend service.

### CORS Configuration

Backend allows requests from configured origins. Modify in `backend/app/main.py:25-31`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://api.goingmerry-stonks.com",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Common Development Tasks

### Adding a New Screener

1. Define screening logic in new router function in `backend/app/routers/screener.py`
2. Use `MarketDataProvider.get_stock_financials()` to fetch data
3. Implement scoring function similar to `_calculate_lynch_score()`
4. Add to `/screener/screeners` endpoint list
5. Document criteria and scoring in `backend/ALPHA_ENGINE_GUIDE.md`
6. Write tests in `backend/tests/test_screener.py`

### Adding a New Options Strategy

1. Add strategy type to `StrategyType` union in `frontend/src/types/options.ts`
2. Implement P/L calculation in `frontend/src/utils/profitLossCalculator.ts`
3. Add metrics calculation in `frontend/src/utils/metricsCalculator.ts`
4. Update strategy selector in `OptionsAnalyzer.tsx`
5. Write tests for the new strategy

### Debugging Production Issues

**Check Cloud Run logs**:
```bash
# View recent logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=100

# Tail logs in real-time
gcloud run services logs tail prod-backend-api --region=us-east5

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=50
```

**Check database status**:
```bash
# Database instance status
gcloud sql instances describe prod-postgres-d05b2fe9

# Connect to database
gcloud sql connect prod-postgres-d05b2fe9 --user=app_user --database=goingmerry_stonks
```

**Check Cloud Run metrics**:
```bash
# Service details
gcloud run services describe prod-backend-api --region=us-east5

# Revisions
gcloud run revisions list --service=prod-backend-api --region=us-east5
```

### Updating Infrastructure

```bash
cd terraform/environments/prod

# Make changes to *.tf files

# Preview changes
terraform plan

# Apply changes
terraform apply

# View outputs
terraform output
```

**Important**: Always run `terraform plan` before `terraform apply` to review changes.

### Deploying Frontend Updates

**PRIMARY METHOD - Firebase Hosting** ⭐
```bash
cd frontend
npm run build
firebase deploy --only hosting
```
This deploys to: https://goingmerry-stonks.web.app

**BACKUP METHOD - Cloud Storage** (use only for testing)
```bash
cd frontend
npm run build
gsutil -m rsync -r -d build gs://sylvan-earth-477020-u6-frontend
```

**⚠️ IMPORTANT**: Always use Firebase Hosting for production deployments!

### Working with Secrets

```bash
# View secret metadata
gcloud secrets describe prod-polygon-api-key

# Access secret value (requires secretAccessor role)
gcloud secrets versions access latest --secret=prod-polygon-api-key

# Update secret
echo -n "new_value" | gcloud secrets versions add prod-polygon-api-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding prod-polygon-api-key \
  --member="serviceAccount:prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Testing Infrastructure

### Backend Testing (pytest)

**Test Categories**:
- Unit tests: 44 tests (core functionality)
- Security tests: 3 tests (input validation, injection prevention)
- Integration tests: 2 tests (skipped in CI, require production API key)

**Coverage Requirements**:
- Minimum: 54% (enforced by CI/CD)
- Target: 70%+ (future goal)

**Running Tests**:
```bash
cd backend

# All tests
pytest

# With coverage report
pytest --cov --cov-report=term-missing --cov-report=html

# Specific test file
pytest tests/test_screener.py -v

# Skip integration tests
pytest -m "not integration"

# Quality checks
black app/ tests/           # Format code
flake8 app/ tests/          # Lint code
mypy app/                   # Type check
bandit -r app/              # Security scan
```

### Frontend Testing (Jest + React Testing Library)

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Update snapshots
npm test -- -u

# Run specific test file
npm test -- MetricsDisplay.test.tsx
```

### Load Testing (Production)

```bash
# Simple load test with curl
for i in {1..100}; do
  curl https://api.goingmerry-stonks.com/health &
done
wait

# Check Cloud Run auto-scaling
gcloud run services describe prod-backend-api --region=us-east5 --format="value(status.conditions)"
```

---

## Monitoring & Observability

### Cloud Monitoring Alerts

Configured alerts (email: brian.boatright@gmail.com):
1. **High Error Rate**: >5% 5xx errors over 5 minutes
2. **High Latency**: P95 latency >2 seconds
3. **Database High Connections**: >80% of max connections

### Key Metrics to Monitor

- **Request Count**: `run.googleapis.com/request_count`
- **Request Latency**: `run.googleapis.com/request_latencies`
- **Error Rate**: `run.googleapis.com/request_count` (filtered by 5xx)
- **Database Connections**: `cloudsql.googleapis.com/database/postgresql/num_backends`
- **CPU Utilization**: `run.googleapis.com/container/cpu/utilizations`
- **Memory Utilization**: `run.googleapis.com/container/memory/utilizations`

### Viewing Metrics

```bash
# Cloud Run metrics dashboard
gcloud monitoring dashboards list

# Query specific metric
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --format="table(metric.type, resource.labels.service_name)"
```

---

## Resource Optimization & Cost Management

### Batch Screener Resource Allocation (November 2025)

The screener jobs have been optimized based on empirical production data to reduce costs while maintaining performance:

**Current Allocation** (per job):
- **Memory**: 512Mi (reduced from 2Gi)
- **CPU**: 1 core (reduced from 2 cores)
- **Cost Savings**: ~52% reduction vs original allocation

**Validation Process**:
1. **Initial Deployment**: Conservative allocation (2Gi/2CPU) based on worst-case estimates
2. **Production Monitoring**: Tracked actual resource usage over 2 weeks (Nov 2025)
3. **Observed Metrics**:
   - Peak memory usage: ~300Mi (40% below optimized limit)
   - Average memory usage: ~250Mi
   - CPU utilization: <50% sustained on 1 core
   - Zero OOM errors or job failures
   - All 10 batch jobs completing successfully daily
   - No impact on API rate limits (50 req/min regular, 36 req/min Smart Money)
4. **Right-Sizing**: Reduced to 512Mi/1CPU (provides 70% memory headroom)
5. **Ongoing Monitoring**: Alerts configured for memory >80% and CPU >90%

**Why This Works**:
- **I/O-Bound Workload**: Jobs spend most time waiting for API responses (rate-limited)
- **Efficient Data Handling**: Streaming processing, minimal caching per ticker
- **ThreadPoolExecutor**: 12 workers are I/O-bound, not CPU-intensive (waiting on network)
- **Batch Size**: ~1200 stocks per batch keeps memory footprint manageable

### Resource Optimization Best Practices

When optimizing Cloud Run jobs or services, follow this methodology:

#### 1. **Profile Before Optimizing**
```bash
# Monitor actual resource usage (Cloud Logging)
gcloud logging read "resource.type=cloud_run_job \
  AND jsonPayload.message=~'Resource usage'" \
  --limit=100 --format=json

# View memory and CPU metrics (Cloud Monitoring)
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision" \
  AND metric.type="run.googleapis.com/container/memory/utilizations"' \
  --format="table(metric.type, point.value.double_value)"
```

#### 2. **Test Changes in Production** (with safeguards)
- Deploy optimized resources during low-traffic periods
- Monitor for 1-2 weeks to capture edge cases
- Set up alerts BEFORE reducing resources:
  ```bash
  # Alert for high memory usage
  gcloud alpha monitoring policies create \
    --condition-threshold-value=0.8 \
    --condition-display-name="Memory > 80%" \
    --display-name="Job High Memory Warning"
  ```

#### 3. **Maintain Headroom**
- **Memory**: Keep 30-50% headroom for traffic spikes
- **CPU**: Keep 40-60% headroom for retry bursts
- **Never run at >90% sustained usage** - risk of OOM kills or throttling

#### 4. **Document Optimizations**
Include in commit messages and Terraform comments:
- Previous allocation vs new allocation
- Observed metrics that justified the change
- Validation period and results
- Cost savings achieved

**Example**:
```hcl
# Optimized based on production metrics (Nov 2025):
# - Observed peak memory: ~300Mi (512Mi provides 70% headroom)
# - CPU utilization: <50% sustained at 1 core
# - Zero OOM errors over 2-week validation period
# - Cost reduction: ~52% vs original (2Gi/2CPU)
job_memory = "512Mi"
job_cpu    = "1"
```

#### 5. **Set Up Monitoring for Regressions**

**Critical Metrics** (alert thresholds):
| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Memory Usage | >80% | >90% | Increase allocation |
| CPU Usage | >80% | >90% | Add CPU cores |
| OOM Errors | >0 | >2/day | Immediate increase |
| Job Failures | >5% | >10% | Investigate + rollback |
| Rate Limit Hits | >10/hour | >50/hour | Reduce concurrency |

**Monitoring Dashboard**:
```bash
# View job execution metrics
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "Screener Jobs - Resource Optimization",
  "gridLayout": {
    "widgets": [
      {
        "title": "Memory Utilization",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_job\" metric.type=\"run.googleapis.com/container/memory/utilizations\""
              }
            }
          }]
        }
      },
      {
        "title": "CPU Utilization",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_job\" metric.type=\"run.googleapis.com/container/cpu/utilizations\""
              }
            }
          }]
        }
      }
    ]
  }
}
EOF
```

#### 6. **Cost Tracking**

Calculate savings from optimizations:

```bash
# Cloud Run pricing (us-east5, Nov 2025):
# - Memory: $0.0000025/GiB-second
# - CPU: $0.00002400/vCPU-second
# - Execution time: ~95 minutes/batch × 10 batches/day × 22 days/month

# Before: 2GiB, 2 vCPU, 95 min/batch, 10 batches/day
# Memory: 2 × 5700s × 10 × 22 × $0.0000025 = $6.27/month
# CPU: 2 × 5700s × 10 × 22 × $0.00002400 = $60.19/month
# Total: ~$66/month

# After: 0.5GiB, 1 vCPU, 95 min/batch, 10 batches/day
# Memory: 0.5 × 5700s × 10 × 22 × $0.0000025 = $1.57/month
# CPU: 1 × 5700s × 10 × 22 × $0.00002400 = $30.10/month
# Total: ~$32/month

# Savings: $34/month (~52% reduction)
```

### Responding to Resource Pressure

If you observe degraded performance after optimization:

**Symptoms**:
- Increasing memory usage trend (approaching limit)
- Job execution time increasing
- Intermittent OOM errors
- Rate limit errors despite correct API limiting

**Response**:
1. **Immediate**: Increase resources by 50% (512Mi→768Mi or 1CPU→1.5CPU)
2. **Investigate**: Check logs for memory leaks, inefficient queries, or traffic changes
3. **Long-term**: Either fix inefficiency or accept higher resource requirements
4. **Document**: Update comments with new metrics and justification

**Rollback Command**:
```bash
# Quick rollback via Terraform
cd terraform/environments/prod
# Edit main.tf: job_memory = "1Gi", job_cpu = "2"
terraform apply -target=module.scheduled_jobs

# Or via gcloud (faster)
gcloud run jobs update prod-regular-screeners-batch-1 \
  --memory=1Gi --cpu=2 --region=us-east5
```

---

## Security Considerations

### Production Security Features

- ✅ **Cloud Armor**: Rate limiting (100 req/min per IP), geo-blocking (Russia), SQL injection protection, XSS protection
- ✅ **Secret Manager**: All credentials encrypted at rest (AES-256)
- ✅ **IAM Least Privilege**: Service accounts have minimal required permissions
- ✅ **VPC Isolation**: Database on private VPC, no public IP
- ✅ **SSL/TLS**: Managed certificates with auto-renewal
- ✅ **HTTPS Enforcement**: HTTP → HTTPS redirect
- ✅ **Container Scanning**: Automated vulnerability scanning in Artifact Registry
- ✅ **Audit Logging**: All API calls and admin actions logged
- ✅ **Firestore Security Rules**: Environment-specific rules with service account restrictions

### Security Best Practices

1. **Never commit sensitive data**:
   - `.env` files (in .gitignore)
   - `terraform.tfvars` files (in .gitignore)
   - API keys or passwords
   - Service account keys

2. **Use Secret Manager** for all production credentials

3. **Follow least privilege**:
   - Service accounts have only necessary permissions
   - Cloud Run ingress: Load Balancer only (no public access)

4. **Regular updates**:
   - Keep dependencies updated (`pip list --outdated`, `npm outdated`)
   - Monitor security advisories (Dependabot, Snyk)
   - Frontend uses npm overrides to enforce secure dependency versions (glob@10.5.0, test-exclude@7.0.1, postcss@8.4.31, webpack-dev-server@5.2.1)

**Recent Security Fixes** (November 27, 2025):
- ✅ **glob CLI vulnerability (CVE-2025-GHSA-5j98-mcp5-4vw2)**: Fixed command injection vulnerability in glob package by upgrading to v10.5.0 via npm overrides
- ✅ **test-exclude compatibility**: Upgraded to v7.0.1 for compatibility with glob@10.x
- ✅ **postcss vulnerability**: Upgraded to v8.4.31 to address parsing error CVE
- ✅ **webpack-dev-server vulnerability**: Upgraded to v5.2.1 to address source code exposure risks
- **Verification**: All 50 tests passing, production build successful, 0 npm audit vulnerabilities

### Firestore Security Rules

Firestore security rules are environment-specific to prevent hardcoding and improve security:

**Structure**:
- `firestore/firestore.rules.template` - Template with placeholders
- `firestore/firestore.rules.prod` - Production rules (sylvan-earth-477020-u6)
- `firestore/firestore.rules.dev` - Development rules (update with dev project)
- `firestore.rules` - Active rules (copied from environment-specific file)

**Deployment**:
```bash
# Using deployment script (recommended)
./scripts/deploy-firestore-rules.sh prod

# Manual deployment
cp firestore/firestore.rules.prod firestore.rules
firebase deploy --only firestore:rules --project goingmerry-stonks
```

**Security Model**:
- ✅ **Public Read**: Anyone can read screener results (fast frontend loading)
- ✅ **Service Account Write**: Only `prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com` can write
- ✅ **Environment Separation**: Each environment has its own service account
- ✅ **Default Deny**: All other access is denied by default

See `firestore/README.md` for detailed documentation.

---

## File Naming and Organization

- **Backend**: Snake_case for Python files (`market_data.py`, `options_pricing.py`)
- **Frontend**: PascalCase for components (`OptionsGrid.tsx`), camelCase for utilities (`metricsCalculator.ts`)
- **Models**: Match their domain (`options.py` for options models, `screener.py` for screener models)
- **Test files**: Prefixed with `test_` and colocated in `backend/tests/` directory
- **Infrastructure**: Terraform files in `terraform/` with modules structure

---

## Important Notes for Development

- **Polygon.io Rate Limits**: Free tier has strict limits (5 calls/min); implement caching for production
- **Cloud Run Cold Starts**: First request after idle may be slow; min_instances=1 configured
- **Database Connections**: Cloud SQL has connection limits; use connection pooling
- **Resource Optimization**: Batch jobs optimized to 512Mi/1CPU based on production profiling (Nov 2025); monitor memory >80% and CPU >90% for regressions
- **Type Safety**: Always define TypeScript interfaces for new data structures
- **Error Handling**: Backend uses custom exceptions; frontend should handle HTTP errors gracefully
- **Logging**: Use `logger.info()` for key operations, `logger.warning()` for recoverable errors, `logger.error()` for failures
- **Testing**: Write tests for new features; maintain ≥54% coverage
- **Documentation**: Update relevant .md files when adding features; document resource changes with observed metrics

---

## Production URLs & Access

### Public URLs
- **API Documentation**: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs
- **API Base URL**: https://api.goingmerry-stonks.com (pending DNS)
- **Frontend**: https://api.goingmerry-stonks.com (pending DNS)
- **Load Balancer IP**: 34.8.254.23

### GCP Console Links
- **Cloud Run**: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
- **Cloud SQL**: https://console.cloud.google.com/sql/instances?project=sylvan-earth-477020-u6
- **Load Balancing**: https://console.cloud.google.com/net-services/loadbalancing?project=sylvan-earth-477020-u6
- **Cloud Storage**: https://console.cloud.google.com/storage/browser?project=sylvan-earth-477020-u6
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager?project=sylvan-earth-477020-u6
- **Logs**: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6
- **Monitoring**: https://console.cloud.google.com/monitoring?project=sylvan-earth-477020-u6

---

## Additional Documentation

- **[README.md](README.md)** - Comprehensive project overview and getting started guide
- **[TESTING.md](TESTING.md)** - Complete testing infrastructure documentation
- **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** - Current deployment status and verification
- **[FRONTEND_DEPLOYMENT.md](FRONTEND_DEPLOYMENT.md)** - Frontend deployment details (Cloud Storage vs Firebase)
- **[backend/ALPHA_ENGINE_GUIDE.md](backend/ALPHA_ENGINE_GUIDE.md)** - Stock screener documentation
- **[frontend/COMPONENTS.md](frontend/COMPONENTS.md)** - Component API reference
- **[frontend/INTEGRATION_GUIDE.md](frontend/INTEGRATION_GUIDE.md)** - Frontend integration patterns
- **[frontend/PROFIT_LOSS_CHART_GUIDE.md](frontend/PROFIT_LOSS_CHART_GUIDE.md)** - P/L chart usage and customization

---

## Quick Reference Commands

```bash
# Local development
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm start

# Run tests
cd backend && pytest --cov
cd frontend && npm test

# Build for production
cd backend && docker build -t api:latest .
cd frontend && npm run build

# Deploy backend
gcloud run deploy prod-backend-api --image=IMAGE_URL --region=us-east5

# Deploy frontend (PRIMARY - Firebase Hosting)
cd frontend && npm run build && firebase deploy --only hosting

# Deploy frontend (BACKUP - Cloud Storage)
cd frontend && npm run build && gsutil -m rsync -r -d build gs://sylvan-earth-477020-u6-frontend

# View logs
gcloud run services logs tail prod-backend-api --region=us-east5

# Infrastructure updates
cd terraform/environments/prod && terraform plan && terraform apply
```

---

**Last Updated**: November 27, 2025 (Security updates: glob@10.5.0, zero npm vulnerabilities)
**Production Status**: ✅ Deployed and operational
**Frontend URL**: https://goingmerry-stonks.web.app (Firebase Hosting)
**Backend URL**: https://prod-backend-api-rlfl2vcoda-ul.a.run.app
**Test Coverage**: 54% (46/46 tests passing, frontend: 50/50 tests passing)
**Resource Allocation**: Optimized (512Mi/1CPU per job, 52% cost reduction validated Nov 2025)
**Security Status**: ✅ 0 vulnerabilities (verified Nov 27, 2025)
