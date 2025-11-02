# Alpha Engine - Stock Screening Module

**Professional stock screening system for identifying investment opportunities**

---

## Overview

The **Alpha Engine** module provides sophisticated stock screening capabilities based on proven investment strategies. It analyzes stocks across multiple financial metrics to identify companies that meet specific criteria, helping investors discover potential opportunities.

### Current Features

✅ **Lynch Fast Growers** - Peter Lynch's growth investing strategy
✅ **Customizable Parameters** - Adjust screening criteria via query parameters
✅ **Detailed Results** - Comprehensive financial metrics for each stock
✅ **Scoring System** - Ranked results based on strategy fit
✅ **Reasoning Engine** - Explains why each stock passed screening

### Planned Features

🔄 **Value Screener** - Benjamin Graham's value investing principles
🔄 **Dividend Aristocrats** - High-quality dividend growth stocks
🔄 **Momentum Screener** - Stocks with strong price momentum
🔄 **Quality Screener** - High-quality businesses (Buffett-style)

---

## API Endpoints

### 1. Lynch Fast Growers Screener

Screen for fast-growing companies using Peter Lynch's investment philosophy.

**Endpoint:** `GET /screener/lynch-fast-growers`

**Strategy Philosophy:**

Peter Lynch, legendary Fidelity Magellan Fund manager, developed the "Fast Growers" strategy to identify companies in early growth phases with 20-25% annual earnings growth, trading at reasonable valuations.

**Screening Criteria:**

1. **Strong Earnings Growth** (10-25% annually)
   - Companies growing faster than the market
   - Sustainable growth rates
   - Not too fast to be unsustainable (>50% may be temporary)

2. **Reasonable Valuation** (PEG ratio < 2.5)
   - PEG = PE Ratio / Earnings Growth Rate
   - Lynch's rule: PEG < 1.0 is excellent, < 2.0 is good
   - Ensures not overpaying for growth

3. **Financial Stability**
   - Current Ratio > 1.0 (can pay short-term debts)
   - Debt-to-Equity < 2.0 (manageable debt levels)
   - Strong balance sheet reduces bankruptcy risk

4. **Market Cap Filter**
   - Focus on mid-cap to large-cap stocks (>$1B)
   - More established companies with growth runway
   - Better liquidity for trading

#### Query Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `min_earnings_growth` | float | 10.0 | 0-1000 | Minimum annual earnings growth rate (%) |
| `max_peg_ratio` | float | 2.5 | 0-10 | Maximum PEG ratio |
| `min_current_ratio` | float | 1.0 | 0-10 | Minimum current ratio (liquidity) |
| `max_debt_to_equity` | float | 2.0 | 0-10 | Maximum debt-to-equity ratio |
| `min_market_cap` | float | 1.0 | 0.1-10000 | Minimum market cap (billions) |
| `limit` | int | 20 | 1-100 | Maximum number of results |

#### Example Request

```bash
# Default parameters
curl "http://localhost:8000/screener/lynch-fast-growers"

# Custom parameters - Aggressive growth
curl "http://localhost:8000/screener/lynch-fast-growers?min_earnings_growth=20&max_peg_ratio=2.0&limit=10"

# Custom parameters - Conservative growth
curl "http://localhost:8000/screener/lynch-fast-growers?min_earnings_growth=12&max_peg_ratio=1.5&min_current_ratio=1.5&max_debt_to_equity=1.0"
```

#### Response Format

```json
{
  "screener_name": "Lynch Fast Growers",
  "description": "Peter Lynch's Fast Growers strategy: Companies with strong earnings growth (10-25%), reasonable PEG ratios, and solid financials",
  "total_results": 8,
  "timestamp": "2025-01-17T10:30:00",
  "criteria": {
    "min_earnings_growth": 10.0,
    "max_peg_ratio": 2.5,
    "min_current_ratio": 1.0,
    "max_debt_to_equity": 2.0,
    "min_market_cap": 1.0
  },
  "results": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "sector": "Technology",
      "market_cap": 1200.5,
      "price": 495.22,
      "pe_ratio": 65.3,
      "peg_ratio": 1.8,
      "revenue_growth": 125.5,
      "earnings_growth": 35.2,
      "debt_to_equity": 0.45,
      "current_ratio": 3.45,
      "score": 92.5,
      "reasons": [
        "Exceptional earnings growth (35.2%)",
        "Excellent PEG ratio (1.8)",
        "Strong financial health",
        "Low debt levels"
      ]
    }
    // ... more stocks
  ]
}
```

#### Response Fields

**Top-Level Fields:**

- `screener_name` (string): Name of the screening strategy
- `description` (string): Strategy description and criteria
- `total_results` (int): Number of stocks that passed screening
- `timestamp` (datetime): When the screening was performed
- `criteria` (object): Parameters used for screening

**Stock Result Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock ticker symbol (e.g., "NVDA") |
| `company_name` | string | Full company name |
| `sector` | string | Industry sector (e.g., "Technology") |
| `market_cap` | float | Market capitalization in billions |
| `price` | float | Current stock price |
| `pe_ratio` | float | Price-to-Earnings ratio |
| `peg_ratio` | float | Price/Earnings to Growth ratio |
| `revenue_growth` | float | Revenue growth rate (%) |
| `earnings_growth` | float | Earnings growth rate (%) |
| `debt_to_equity` | float | Debt-to-Equity ratio |
| `current_ratio` | float | Current ratio (liquidity metric) |
| `score` | float | Screening score (0-100, higher is better) |
| `reasons` | array[string] | Why this stock passed screening |

---

### 2. List Available Screeners

Get information about all available screening strategies.

**Endpoint:** `GET /screener/screeners`

#### Example Request

```bash
curl "http://localhost:8000/screener/screeners"
```

#### Response Format

```json
{
  "total_screeners": 4,
  "alpha_engine_version": "1.0.0",
  "screeners": [
    {
      "name": "Lynch Fast Growers",
      "endpoint": "/screener/lynch-fast-growers",
      "description": "Peter Lynch's strategy for finding fast-growing companies",
      "criteria": [
        "Earnings growth: 10-25% annually",
        "PEG ratio < 2.5",
        "Current ratio > 1.0",
        "Debt-to-equity < 2.0"
      ],
      "ideal_for": "Growth investors seeking undervalued high-growth stocks",
      "risk_level": "Medium",
      "typical_holding_period": "2-5 years"
    },
    {
      "name": "Value Screener",
      "endpoint": "/screener/value",
      "description": "Coming soon - Benjamin Graham value investing strategy",
      "status": "planned"
    }
    // ... more screeners
  ]
}
```

---

## Understanding the Metrics

### Growth Metrics

**Earnings Growth Rate**
- Percentage increase in earnings per share (EPS) year-over-year
- Lynch's sweet spot: 20-25% annually
- Too high (>50%) may be unsustainable
- Too low (<10%) may not outperform market

**Revenue Growth Rate**
- Percentage increase in total revenue year-over-year
- Confirms earnings growth is from business expansion, not cost-cutting
- Healthy companies have revenue growth ≥ earnings growth

### Valuation Metrics

**PEG Ratio** (Price/Earnings to Growth)
```
PEG = PE Ratio / Earnings Growth Rate
```
- Lynch's favorite metric for growth stocks
- PEG < 1.0: Undervalued relative to growth (excellent)
- PEG 1.0-2.0: Fairly valued (good)
- PEG > 2.0: May be overvalued (caution)

**PE Ratio** (Price-to-Earnings)
```
PE = Stock Price / Earnings Per Share
```
- How much investors pay per dollar of earnings
- High PE = high growth expectations
- Low PE = value opportunity or trouble

### Financial Health Metrics

**Current Ratio** (Liquidity)
```
Current Ratio = Current Assets / Current Liabilities
```
- Measures ability to pay short-term debts
- > 1.5: Healthy (can easily pay debts)
- 1.0-1.5: Acceptable
- < 1.0: Potential liquidity problems

**Debt-to-Equity Ratio**
```
D/E = Total Debt / Shareholder Equity
```
- Measures financial leverage
- < 1.0: Conservative (good for stability)
- 1.0-2.0: Moderate (acceptable for most industries)
- > 2.0: High leverage (risky)

---

## Scoring System

Each stock receives a score (0-100) based on how well it meets the screening criteria:

### Score Calculation (Lynch Fast Growers)

**Earnings Growth** (35 points)
- 30+ points: Growth > 25%
- 20-29 points: Growth 15-25%
- 10-19 points: Growth 10-15%
- 0-9 points: Growth < 10%

**PEG Ratio** (30 points)
- 30 points: PEG < 1.0
- 20-29 points: PEG 1.0-1.5
- 10-19 points: PEG 1.5-2.0
- 0-9 points: PEG > 2.0

**Financial Health** (20 points)
- 10 points: Current ratio > 2.0
- 5 points: Current ratio 1.5-2.0
- 2 points: Current ratio 1.0-1.5
- 10 points: D/E < 0.5
- 5 points: D/E 0.5-1.0
- 2 points: D/E 1.0-2.0

**Revenue Growth** (15 points)
- 15 points: Revenue growth > 20%
- 10 points: Revenue growth 10-20%
- 5 points: Revenue growth 5-10%
- 0 points: Revenue growth < 5%

**Interpretation:**
- 90-100: Excellent fit for strategy
- 80-89: Strong candidate
- 70-79: Good candidate
- 60-69: Acceptable
- <60: Marginal fit

---

## Investment Strategies Guide

### Lynch Fast Growers Strategy

**When to Use:**
- Bull markets or market recoveries
- Looking for 2-5 year holdings
- Willing to accept moderate volatility
- Seeking capital appreciation over income

**What to Look For:**
1. **Sustainable Growth** - Can the company maintain growth for 3-5 years?
2. **Competitive Advantage** - Does it have a moat?
3. **Management Quality** - Strong leadership executing on vision
4. **Industry Tailwinds** - Secular growth trends (AI, cloud, etc.)

**Red Flags:**
- PEG > 2.5 (overpaying for growth)
- Earnings growth > 50% (likely temporary)
- Deteriorating margins (cost pressures)
- High debt with slowing growth (dangerous combination)

**Exit Signals:**
- Growth rate slows below 10%
- PEG exceeds 3.0
- Financial health deteriorates
- Competitive position weakens

**Historical Performance:**
- Lynch achieved 29% annual returns at Fidelity (1977-1990)
- Beat S&P 500 by ~10% annually
- Strategy works best in growth-friendly environments

---

## Integration Examples

### Python Example

```python
import requests

# Basic screening
response = requests.get('http://localhost:8000/screener/lynch-fast-growers')
data = response.json()

for stock in data['results']:
    print(f"{stock['ticker']}: {stock['company_name']}")
    print(f"  Score: {stock['score']}")
    print(f"  PEG Ratio: {stock['peg_ratio']}")
    print(f"  Earnings Growth: {stock['earnings_growth']}%")
    print(f"  Reasons: {', '.join(stock['reasons'])}")
    print()

# Custom parameters
params = {
    'min_earnings_growth': 15.0,
    'max_peg_ratio': 2.0,
    'min_market_cap': 5.0,
    'limit': 10
}
response = requests.get('http://localhost:8000/screener/lynch-fast-growers', params=params)
aggressive_growth = response.json()
```

### JavaScript Example

```javascript
// Fetch screening results
async function getLynchFastGrowers(params = {}) {
  const queryString = new URLSearchParams(params).toString();
  const url = `http://localhost:8000/screener/lynch-fast-growers?${queryString}`;

  const response = await fetch(url);
  const data = await response.json();

  return data;
}

// Example usage
const screenerResults = await getLynchFastGrowers({
  min_earnings_growth: 15,
  max_peg_ratio: 2.0,
  limit: 20
});

console.log(`Found ${screenerResults.total_results} stocks`);
screenerResults.results.forEach(stock => {
  console.log(`${stock.ticker}: Score ${stock.score}`);
});
```

### React Component Example

```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ScreenerResult {
  ticker: string;
  company_name: string;
  score: number;
  peg_ratio: number;
  earnings_growth: number;
  reasons: string[];
}

const LynchScreener: React.FC = () => {
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchResults = async (minGrowth: number = 10) => {
    setLoading(true);
    try {
      const response = await axios.get(
        'http://localhost:8000/screener/lynch-fast-growers',
        { params: { min_earnings_growth: minGrowth } }
      );
      setResults(response.data.results);
    } catch (error) {
      console.error('Screening error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  return (
    <div className="lynch-screener">
      <h2>Lynch Fast Growers</h2>
      {loading ? (
        <p>Screening stocks...</p>
      ) : (
        <ul>
          {results.map(stock => (
            <li key={stock.ticker}>
              <strong>{stock.ticker}</strong> - {stock.company_name}
              <br />
              Score: {stock.score} | PEG: {stock.peg_ratio} | Growth: {stock.earnings_growth}%
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LynchScreener;
```

---

## Error Handling

### Common Errors

**400 Bad Request**
```json
{
  "detail": [
    {
      "loc": ["query", "min_earnings_growth"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```
**Cause:** Invalid parameter values (e.g., negative growth rate)
**Solution:** Check parameter ranges in API documentation

**500 Internal Server Error**
```json
{
  "detail": "Internal server error"
}
```
**Cause:** Server-side error (data source unavailable, calculation error)
**Solution:** Check server logs, retry request

### Best Practices

1. **Validate Parameters** - Check ranges before sending requests
2. **Handle Timeouts** - Screening can take time, set appropriate timeouts
3. **Cache Results** - Avoid excessive API calls, cache for 1-5 minutes
4. **Error Recovery** - Implement retry logic with exponential backoff
5. **Rate Limiting** - Respect API rate limits (if implemented)

---

## Roadmap

### Phase 1: Foundation ✅
- [x] Lynch Fast Growers screener
- [x] Pydantic models for validation
- [x] RESTful API design
- [x] Comprehensive documentation

### Phase 2: Data Integration 🔄
- [ ] Real-time market data integration
- [ ] Historical data for backtesting
- [ ] Fundamental data from financial APIs
- [ ] Data caching and optimization

### Phase 3: Additional Screeners 📋
- [ ] Value Screener (Graham)
- [ ] Dividend Aristocrats
- [ ] Momentum Screener
- [ ] Quality Screener (Buffett-style)
- [ ] GARP (Growth at Reasonable Price)

### Phase 4: Advanced Features 📋
- [ ] Backtesting capabilities
- [ ] Custom screener builder
- [ ] Alert system for new matches
- [ ] Portfolio screening
- [ ] Sector rotation analysis
- [ ] Peer comparison

### Phase 5: Analytics 📋
- [ ] Performance tracking
- [ ] Strategy comparison
- [ ] Risk analytics
- [ ] Correlation analysis
- [ ] Historical success rates

---

## Technical Architecture

### Data Models

**StockScreenerResult**
- Represents a single stock that passed screening
- Contains 12+ financial metrics
- Includes scoring and reasoning

**ScreenerResponse**
- Complete API response wrapper
- Metadata: timestamp, criteria, totals
- Array of StockScreenerResult objects

**ScreenerCriteria**
- Defines screening parameters
- Validates input ranges
- Provides defaults

### Router Design

**Separation of Concerns:**
- `/routers/screener.py` - API endpoints and request handling
- `/models/screener.py` - Data validation and serialization
- `/services/screener_engine.py` (future) - Screening logic and calculations

**Extensibility:**
- Easy to add new screeners
- Shared models and utilities
- Consistent API patterns

### Performance Considerations

**Current (Placeholder):**
- O(1) response time (static data)
- No database queries
- Minimal memory usage

**Future (Production):**
- Database indexing on key fields
- Caching layer (Redis) for frequent queries
- Async processing for large datasets
- Pagination for large result sets
- Rate limiting to prevent abuse

---

## Contributing

### Adding New Screeners

1. **Define Criteria** - Document investment strategy and metrics
2. **Create Endpoint** - Add route to `/routers/screener.py`
3. **Implement Logic** - Screen stocks based on criteria
4. **Add Tests** - Unit tests for calculation logic
5. **Update Docs** - Add to this guide

**Example Template:**
```python
@router.get("/your-strategy", response_model=ScreenerResponse)
async def get_your_strategy(
    param1: float = Query(default, ge=min, le=max),
    # ... more parameters
) -> ScreenerResponse:
    """
    Screen stocks using Your Strategy.

    [Detailed strategy description]
    """
    # Implementation here
```

### Testing

**Unit Tests:**
```bash
pytest backend/tests/test_screener.py
```

**Integration Tests:**
```bash
pytest backend/tests/test_screener_integration.py
```

**API Tests:**
```bash
curl http://localhost:8000/screener/lynch-fast-growers
```

---

## References

### Books
- **One Up On Wall Street** by Peter Lynch - Original Fast Growers strategy
- **The Intelligent Investor** by Benjamin Graham - Value investing foundation
- **Common Stocks and Uncommon Profits** by Philip Fisher - Quality investing

### Research Papers
- Lynch, P. (1989). "Investing in Fast Growers" - Fidelity Research
- Graham, B. & Dodd, D. (1934). "Security Analysis" - Value investing principles

### APIs & Data Sources
- Polygon.io - Market data and fundamentals
- Alpha Vantage - Financial statements
- Yahoo Finance - Historical data

---

## Support

**Documentation:**
- API Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

**Questions?**
- Check main README.md
- Review COMPONENTS.md for related modules
- See INTEGRATION_GUIDE.md for frontend integration

---

**Built with FastAPI, Pydantic, and proven investment strategies** 📊🚀

*Alpha Engine v1.0.0 - Identifying tomorrow's winners today*
