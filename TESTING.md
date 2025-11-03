# GoingMerry-Stonks Testing Strategy

Comprehensive testing documentation for the fintech platform.

## Testing Philosophy

**For financial applications, testing is NOT optional. It is mandatory.**

### Requirements

- ✅ **80% minimum code coverage** (enforced in CI/CD)
- ✅ **All tests must pass** before deployment
- ✅ **Security scans must pass** before deployment
- ✅ **Linting and type checking** must pass
- ✅ **No known critical vulnerabilities** in dependencies

## Backend Testing (Python/FastAPI)

### Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_main.py             # Health checks, CORS
│   ├── test_options_router.py   # Options API tests
│   ├── test_screener_router.py  # Screener API tests
│   └── test_market_data_service.py  # Service layer tests
├── pytest.ini                   # Pytest configuration
└── requirements-dev.txt         # Test dependencies
```

### Running Tests

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m security       # Security tests only
pytest -m smoke          # Smoke tests only

# Run specific test file
pytest tests/test_options_router.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run failed tests from last run
pytest --lf
```

### Test Categories

Tests are marked with pytest markers:

- **`@pytest.mark.unit`** - Fast, isolated unit tests
- **`@pytest.mark.integration`** - Tests with external dependencies
- **`@pytest.mark.security`** - Security-focused tests
- **`@pytest.mark.slow`** - Long-running tests
- **`@pytest.mark.smoke`** - Basic smoke tests

### Code Quality Checks

```bash
# Black formatting
black app/
black --check app/  # Check without modifying

# Flake8 linting
flake8 app/ --max-line-length=100 --extend-ignore=E203,W503

# MyPy type checking
mypy app/ --ignore-missing-imports

# Bandit security scanning
bandit -r app/ -ll

# Safety vulnerability checking
safety check
```

### Coverage Requirements

Configured in `pytest.ini`:
- **Minimum 80% coverage** (build fails below this)
- Coverage reports in terminal, HTML, and XML formats
- Excludes test files, `__init__.py`, and abstract methods

### Writing Tests

#### Example Unit Test

```python
@pytest.mark.unit
def test_get_option_chain_success(test_client, mock_polygon_api):
    """Test successful option chain retrieval."""
    response = test_client.get("/options/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "calls" in data
    assert "puts" in data
```

#### Example Integration Test

```python
@pytest.mark.integration
def test_option_chain_real_api_call(test_client):
    """Integration test with real Polygon API."""
    if os.getenv("POLYGON_API_KEY") == "test_api_key_12345":
        pytest.skip("Skipping real API test in test environment")

    response = test_client.get("/options/AAPL?limit=5")
    assert response.status_code in [200, 404, 429, 503]
```

#### Example Security Test

```python
@pytest.mark.security
def test_api_key_not_logged():
    """Test that API key is not exposed in logs or errors."""
    provider = MarketDataProvider(api_key="secret_api_key_12345")

    try:
        provider.get_stock_quote("AAPL")
    except Exception as e:
        assert "secret_api_key" not in str(e).lower()
```

### Fixtures

Common fixtures in `conftest.py`:

- **`test_client`** - FastAPI TestClient
- **`mock_polygon_api`** - Mocked Polygon API responses
- **`sample_option_chain`** - Sample option chain data
- **`sample_stock_financials`** - Sample financial data
- **`mock_database`** - Mocked database connection

## Frontend Testing (React/TypeScript)

### Test Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── __tests__/
│   │       └── component.test.tsx
│   └── utils/
│       └── __tests__/
│           └── utility.test.ts
├── setupTests.ts                # Jest configuration
└── package.json                 # Test scripts
```

### Running Tests

```bash
cd frontend

# Install dependencies
npm install

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run linting
npm run lint

# Run type checking
npm run type-check
```

### Test Scripts

Configured in `package.json`:

- **`npm test`** - Run tests with coverage
- **`npm run test:watch`** - Watch mode for development
- **`npm run test:coverage`** - Generate coverage reports
- **`npm run lint`** - ESLint checks
- **`npm run type-check`** - TypeScript validation

### Coverage Requirements

- **Minimum 80% coverage** across branches, functions, lines, and statements
- Excludes: `index.tsx`, `*.d.ts` files, example components
- Coverage reports in terminal and HTML

### Writing Tests

#### Example Component Test

```typescript
import { render, screen } from '@testing-library/react';
import { MetricsDisplay } from '../MetricsDisplay';

test('renders metrics display with correct values', () => {
  const metrics = {
    netCredit: 525,
    maxProfit: 525,
    breakeven: 144.75
  };

  render(<MetricsDisplay metrics={metrics} />);

  expect(screen.getByText(/net credit/i)).toBeInTheDocument();
  expect(screen.getByText('$525')).toBeInTheDocument();
});
```

#### Example Utility Test

```typescript
import { calculateMetrics } from '../metricsCalculator';

describe('metricsCalculator', () => {
  it('should calculate metrics for short put strategy', () => {
    const params = {
      strategyType: 'short_put',
      strike: 150,
      premium: 5.25,
      quantity: 1,
      currentStockPrice: 155
    };

    const metrics = calculateMetrics(params);

    expect(metrics.netCredit).toBeCloseTo(525, 0);
    expect(metrics.breakeven).toBeCloseTo(144.75, 2);
  });
});
```

## CI/CD Integration

### Docker Build Process

Both Dockerfiles include **mandatory test stages**:

#### Backend Dockerfile

```dockerfile
# Stage 1: Test
FROM python:3.11-slim as test
# ... install dependencies ...
RUN black --check app/ || exit 1
RUN flake8 app/ || exit 1
RUN mypy app/ || exit 1
RUN bandit -r app/ -ll || exit 1
RUN pytest --cov-fail-under=80 || exit 1

# Stage 2: Production (only if tests pass)
FROM python:3.11-slim
COPY --from=test /app/app ./app
```

#### Frontend Dockerfile

```dockerfile
# Stage 1: Test
FROM node:18-alpine as test
RUN npm run lint || exit 1
RUN npm run type-check || exit 1
RUN npm run test:coverage || exit 1
RUN npm run build

# Stage 2: Production (only if tests pass)
FROM nginx:1.25-alpine
COPY --from=test /app/build /usr/share/nginx/html
```

### Cloud Build Pipeline

```yaml
steps:
  # 1. Backend quality checks
  - name: python:3.11-slim
    id: backend-quality-checks
    # ... black, flake8, mypy ...

  # 2. Backend security scan
  - name: python:3.11-slim
    id: backend-security-scan
    # ... bandit, safety ...

  # 3. Backend tests
  - name: python:3.11-slim
    id: backend-tests
    # ... pytest with coverage ...

  # 4. Frontend quality checks
  - name: node:18-alpine
    id: frontend-quality-checks
    # ... eslint, type-check ...

  # 5. Frontend tests
  - name: node:18-alpine
    id: frontend-tests
    # ... jest with coverage ...

  # 6-7. Build Docker images (only if tests pass)
  # 8-9. Deploy (only if builds succeed)
  # 10-11. Smoke tests (validate deployment)
```

### GitHub Actions Pipeline

```yaml
jobs:
  backend-tests:
    steps:
      - Black formatting check
      - Flake8 linting
      - MyPy type checking
      - Bandit security scan
      - Pytest with coverage ≥ 80%

  frontend-tests:
    steps:
      - ESLint
      - TypeScript type checking
      - Jest with coverage ≥ 80%

  backend-deploy:
    needs: backend-tests
    steps:
      - Build Docker (runs tests inside)
      - Deploy to Cloud Run
      - Health check

  frontend-deploy:
    needs: frontend-tests
    steps:
      - Build production bundle
      - Deploy to Firebase
      - Health check
```

## Test Data & Mocking

### Backend Mocking

We use `unittest.mock` and `responses` for mocking:

```python
@pytest.fixture
def mock_polygon_api():
    """Mock Polygon.io API responses."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {...}
        mock_get.return_value = mock_response
        yield mock_get
```

### Frontend Mocking

We use Jest mocks:

```typescript
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

mockedAxios.get.mockResolvedValue({
  data: { ... }
});
```

## Security Testing

### Backend Security

```bash
# Scan for security issues
bandit -r app/ -ll

# Check for known vulnerabilities
safety check --json

# Check for secrets in code
git secrets --scan
```

### Frontend Security

```bash
# Audit npm dependencies
npm audit

# Fix vulnerabilities
npm audit fix

# Check for outdated packages
npm outdated
```

## Performance Testing

### Load Testing (Optional)

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host=https://api.example.com
```

## Best Practices

### DO ✅

- Write tests for ALL new features
- Maintain 80%+ code coverage
- Mock external APIs in tests
- Use descriptive test names
- Test edge cases and error scenarios
- Run tests before committing
- Fix failing tests immediately
- Test security vulnerabilities

### DON'T ❌

- Skip tests to "save time"
- Commit with failing tests
- Lower coverage requirements
- Test implementation details
- Write flaky tests
- Ignore security warnings
- Hardcode credentials in tests
- Disable linters

## Continuous Improvement

### Code Coverage Trends

Monitor coverage over time:

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Test Metrics

Track:
- **Coverage %** - Should trend upward
- **Test count** - Should grow with features
- **Test duration** - Keep tests fast
- **Flaky tests** - Should be zero

## Troubleshooting

### Tests Failing Locally

```bash
# Clean Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name '*.pyc' -delete

# Reinstall dependencies
pip install -r requirements.txt -r requirements-dev.txt --force-reinstall

# Clear pytest cache
pytest --cache-clear
```

### Tests Failing in CI/CD

1. Check environment variables
2. Verify dependencies are installed
3. Check for race conditions
4. Review logs in Cloud Build console

### Coverage Below Threshold

```bash
# Find untested code
pytest --cov=app --cov-report=term-missing

# Focus on uncovered lines
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [Testing Library](https://testing-library.com/)
- [Bandit Security Tool](https://bandit.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Summary

This fintech application has **enterprise-grade testing**:

✅ **80% minimum coverage** enforced at build time
✅ **Multi-stage Docker builds** with test validation
✅ **Comprehensive test suites** (unit, integration, security)
✅ **Automated quality checks** (linting, type checking, security)
✅ **CI/CD test gates** (nothing deploys without passing tests)
✅ **Smoke tests** post-deployment

**No code reaches production without passing all tests and quality checks.**
