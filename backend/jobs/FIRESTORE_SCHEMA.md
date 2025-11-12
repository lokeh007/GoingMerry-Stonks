# Firestore Schema for Daily Screeners

## Overview

Daily screener results are stored in Firestore for instant frontend loading. Results are cached for 30 days and automatically cleaned up.

## Collection Structure

```
firestore/
└── screeners/                              # Root collection
    ├── undiscovered/                        # The Undiscovered screener
    │   ├── metadata/                        # Screener metadata (optional)
    │   │   └── info                         # Document: screener description, last_run, etc.
    │   └── runs/                            # Historical runs
    │       ├── 2025-11-10/                  # Document per day (YYYY-MM-DD)
    │       ├── 2025-11-11/
    │       └── 2025-11-12/
    └── coiled_spring/                       # The Coiled Spring screener
        ├── metadata/
        │   └── info
        └── runs/
            ├── 2025-11-10/
            ├── 2025-11-11/
            └── 2025-11-12/
```

## Document Schema

### screeners/{screener_name}/runs/{YYYY-MM-DD}

Each daily run document contains:

```json
{
  "screener_name": "The Undiscovered",
  "timestamp": "2025-11-10T23:30:00.000Z",
  "total_results": 47,
  "total_screened": 6000,
  "failed_count": 123,
  "execution_time_seconds": 3600,

  "parameters": {
    "max_institutional_ownership": 25.0,
    "max_analyst_coverage": 5,
    "require_insider_buying": true
  },

  "results": [
    {
      "ticker": "ABC",
      "company_name": "ABC Company Inc.",
      "sector": "Technology",
      "current_price": 45.67,
      "market_cap": 1200000000,
      "score": 85.5,

      // Undiscovered-specific fields
      "institutional_ownership": 12.3,
      "analyst_count": 2,
      "has_insider_buying": true,
      "peg_ratio": 0.85,
      "eps_growth": 25.5
    },
    {
      "ticker": "XYZ",
      "company_name": "XYZ Corp",
      "sector": "Healthcare",
      "current_price": 123.45,
      "market_cap": 5600000000,
      "score": 78.2,

      // Coiled Spring-specific fields
      "has_nr7": true,
      "volatility_30d": 12.5,
      "volatility_percentile": 8.2,
      "current_range": 2.45
    }
    // ... up to 100 results
  ]
}
```

## Field Descriptions

### Common Fields (all screeners)
- `screener_name` (string): Human-readable screener name
- `timestamp` (ISO 8601): When the screener was executed
- `total_results` (int): Total stocks that passed all filters
- `total_screened` (int): Total stocks in universe (e.g., 6000)
- `failed_count` (int): Stocks that errored during screening
- `execution_time_seconds` (float): Time to complete screening
- `parameters` (object): Filters used for this run
- `results` (array): Top 100 stocks sorted by score

### Result Object Fields
- `ticker` (string): Stock symbol (uppercase)
- `company_name` (string): Company name from yfinance
- `sector` (string): Industry sector
- `current_price` (float|null): Current stock price
- `market_cap` (float|null): Market capitalization in USD
- `score` (float): Screener-specific score (0-100)

### The Undiscovered - Specific Fields
- `institutional_ownership` (float): % institutional ownership
- `analyst_count` (int): Number of analysts covering stock
- `has_insider_buying` (bool): Recent insider net purchases
- `peg_ratio` (float|null): PEG ratio
- `eps_growth` (float|null): EPS growth rate (%)

### The Coiled Spring - Specific Fields
- `has_nr7` (bool): NR7 pattern detected
- `volatility_30d` (float|null): 30-day historical volatility (%)
- `volatility_percentile` (float|null): Percentile rank of volatility
- `current_range` (float|null): Today's high-low range

## Indexes

Required Firestore indexes for efficient queries:

```
Collection: screeners/{screener_name}/runs
Indexes:
  - timestamp (DESC)
  - total_results (DESC)
```

## Security Rules

Recommended Firestore security rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Screener results are public read, but only Cloud Run Job can write
    match /screeners/{screener}/{document=**} {
      allow read: if true;  // Public read
      allow write: if request.auth != null && request.auth.token.email.matches(".*@.*\\.iam\\.gserviceaccount\\.com");  // Service account only
    }
  }
}
```

## Query Examples

### Frontend: Get Latest Run

```typescript
// Get most recent Undiscovered results
const latestRun = await firestore
  .collection('screeners')
  .doc('undiscovered')
  .collection('runs')
  .orderBy('timestamp', 'desc')
  .limit(1)
  .get();

const data = latestRun.docs[0].data();
console.log(`Last updated: ${data.timestamp}`);
console.log(`Results: ${data.results.length}`);
```

### Get Historical Trend (Last 7 Days)

```typescript
const sevenDaysAgo = new Date();
sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

const recentRuns = await firestore
  .collection('screeners')
  .doc('coiled_spring')
  .collection('runs')
  .where('timestamp', '>=', sevenDaysAgo.toISOString())
  .orderBy('timestamp', 'desc')
  .get();

// Analyze which stocks appear multiple times
const tickerFrequency = {};
recentRuns.forEach(doc => {
  doc.data().results.forEach(result => {
    tickerFrequency[result.ticker] = (tickerFrequency[result.ticker] || 0) + 1;
  });
});
```

## Data Retention

- **Automatic cleanup**: Runs older than 30 days are deleted
- **Storage estimate**: ~400KB per day × 30 days = 12MB total
- **Cost**: Free tier covers this easily (1GB free storage)

## Monitoring

Key metrics to track:

1. **Execution time**: Should stay under 90 minutes
2. **Total results**: Track if screeners are finding fewer stocks
3. **Failed count**: High failure rate indicates API issues
4. **Timestamp gaps**: Missing days indicate job failures

## Future Enhancements

1. **Change detection**: Compare today vs yesterday, highlight new/removed stocks
2. **Alerts**: Email when high-scoring stocks appear
3. **Watchlists**: Allow users to save favorite stocks
4. **Historical charts**: Track score trends over time
5. **Export**: CSV/JSON export of results
