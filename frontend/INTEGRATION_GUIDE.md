# OptionsGrid ↔️ MetricsDisplay Integration Guide

Complete guide for the integrated options analysis system that connects the OptionsGrid and MetricsDisplay components.

---

## Overview

The **OptionsAnalyzer** component provides a seamless integration between:
- **OptionsGrid**: Interactive option chain table
- **MetricsDisplay**: Financial metrics calculator and display

### User Flow

```
1. User views options grid → 2. Clicks on a cell → 3. Selects strategy → 4. Views calculated metrics
```

---

## Architecture

### Component Hierarchy

```
App.tsx
  └── OptionsAnalyzer
      ├── OptionsGrid (displays option chain)
      └── MetricsDisplay (shows calculated metrics)
```

### Data Flow

```
API Response (OptionChainResponse)
    ↓
OptionsAnalyzer (state management)
    ↓
User Clicks Cell (strike + expiration)
    ↓
metricsCalculator.ts (calculate financials)
    ↓
MetricsDisplay (render metrics)
```

---

## Quick Start

### 1. Basic Integration

```tsx
import { OptionsAnalyzer } from './components';

const App = () => {
  const [optionData, setOptionData] = useState(null);

  // Fetch option chain from API
  useEffect(() => {
    axios.get('/options/AAPL')
      .then(res => setOptionData(res.data));
  }, []);

  return (
    <div>
      {optionData && (
        <OptionsAnalyzer
          optionChainData={optionData}
          defaultStrategy="short_put"
        />
      )}
    </div>
  );
};
```

### 2. With Metrics Callback

```tsx
import { OptionsAnalyzer } from './components';
import type { FinancialMetrics } from './types/metrics';

const App = () => {
  const [metrics, setMetrics] = useState<FinancialMetrics | null>(null);

  const handleMetricsCalculated = (calculatedMetrics: FinancialMetrics) => {
    setMetrics(calculatedMetrics);
    console.log('New metrics:', calculatedMetrics);

    // You could:
    // - Save to backend
    // - Track analytics
    // - Update other components
  };

  return (
    <OptionsAnalyzer
      optionChainData={optionData}
      onMetricsCalculated={handleMetricsCalculated}
    />
  );
};
```

---

## Component APIs

### OptionsAnalyzer Props

```typescript
interface OptionsAnalyzerProps {
  // Required: Option chain data from backend
  optionChainData: OptionChainResponse;

  // Optional: Default strategy selection
  defaultStrategy?: 'short_put' | 'short_call' | 'long_call' | 'long_put';

  // Optional: Callback when metrics are calculated
  onMetricsCalculated?: (metrics: FinancialMetrics) => void;

  // Optional: Custom CSS class
  className?: string;
}
```

### Available Strategies

#### 1. Short Put (Cash-Secured) - Default
```typescript
defaultStrategy="short_put"
```
- **Type**: Credit strategy (bullish)
- **Max Profit**: Premium received
- **Max Loss**: Strike price × 100 - premium
- **Collateral**: Full strike price in cash

#### 2. Long Call
```typescript
defaultStrategy="long_call"
```
- **Type**: Debit strategy (bullish)
- **Max Profit**: Unlimited
- **Max Loss**: Premium paid
- **Collateral**: Premium paid

#### 3. Long Put
```typescript
defaultStrategy="long_put"
```
- **Type**: Debit strategy (bearish)
- **Max Profit**: Strike - premium (if stock goes to $0)
- **Max Loss**: Premium paid
- **Collateral**: Premium paid

#### 4. Short Call (Naked)
```typescript
defaultStrategy="short_call"
```
- **Type**: Credit strategy (bearish/neutral)
- **Max Profit**: Premium received
- **Max Loss**: Unlimited (theoretically)
- **Collateral**: 20% margin + premium

---

## Metrics Calculator Utility

### Location
`src/utils/metricsCalculator.ts`

### Core Functions

#### calculateSingleOptionMetrics
Calculate metrics for a single long or short option.

```typescript
import { calculateSingleOptionMetrics } from '../utils/metricsCalculator';

const metrics = calculateSingleOptionMetrics(
  optionContract,  // OptionContract
  stockPrice,      // number
  true            // isLong: true for buy, false for sell
);
```

#### calculateMetricsFromCellData
Calculate metrics from grid cell data (used internally by OptionsAnalyzer).

```typescript
const metrics = calculateMetricsFromCellData(
  strike,          // number
  expiration,      // string (YYYY-MM-DD)
  callBid,         // number | undefined
  callAsk,         // number | undefined
  putBid,          // number | undefined
  putAsk,          // number | undefined
  stockPrice,      // number | undefined
  'short_put'      // strategy
);
```

#### Spread Calculators

```typescript
// Bull Call Spread
const metrics = calculateBullCallSpreadMetrics(
  longCall,   // Lower strike call (bought)
  shortCall,  // Higher strike call (sold)
  stockPrice
);

// Bear Put Spread
const metrics = calculateBearPutSpreadMetrics(
  longPut,    // Higher strike put (bought)
  shortPut,   // Lower strike put (sold)
  stockPrice
);
```

---

## Usage Examples

### Example 1: Basic Setup

```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { OptionsAnalyzer } from './components';

const OptionsPage = () => {
  const [optionData, setOptionData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const response = await axios.get('/options/TSLA?limit=50');
      setOptionData(response.data);
      setLoading(false);
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="options-page">
      <h1>TSLA Options Analysis</h1>
      <OptionsAnalyzer optionChainData={optionData} />
    </div>
  );
};
```

### Example 2: Track User Activity

```tsx
import React, { useState } from 'react';
import { OptionsAnalyzer } from './components';
import type { FinancialMetrics } from './types/metrics';

const AnalyticsExample = () => {
  const [history, setHistory] = useState<FinancialMetrics[]>([]);

  const trackMetrics = (metrics: FinancialMetrics) => {
    // Add to history
    setHistory(prev => [...prev, metrics]);

    // Send to analytics
    analytics.track('option_analyzed', {
      netCredit: metrics.netCredit,
      maxProfit: metrics.maxProfit,
      roc: metrics.returnOnCapital,
    });

    // Save to backend
    axios.post('/api/save-analysis', metrics);
  };

  return (
    <div>
      <OptionsAnalyzer
        optionChainData={optionData}
        onMetricsCalculated={trackMetrics}
      />

      <div className="history">
        <h3>Analysis History</h3>
        {history.map((m, i) => (
          <div key={i}>
            Analysis #{i + 1}: {m.netCredit} credit
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Example 3: Multi-Strategy Comparison

```tsx
const StrategyComparison = () => {
  const [strategy1, setStrategy1] = useState<FinancialMetrics | null>(null);
  const [strategy2, setStrategy2] = useState<FinancialMetrics | null>(null);

  return (
    <div className="comparison-view">
      <div className="strategy-column">
        <h3>Strategy 1: Short Put</h3>
        <OptionsAnalyzer
          optionChainData={optionData}
          defaultStrategy="short_put"
          onMetricsCalculated={setStrategy1}
        />
      </div>

      <div className="strategy-column">
        <h3>Strategy 2: Long Call</h3>
        <OptionsAnalyzer
          optionChainData={optionData}
          defaultStrategy="long_call"
          onMetricsCalculated={setStrategy2}
        />
      </div>

      {/* Comparison Panel */}
      {strategy1 && strategy2 && (
        <div className="comparison-panel">
          <h3>Comparison</h3>
          <table>
            <tr>
              <td>ROC:</td>
              <td>{strategy1.returnOnCapital}%</td>
              <td>{strategy2.returnOnCapital}%</td>
            </tr>
          </table>
        </div>
      )}
    </div>
  );
};
```

### Example 4: Custom Strategy Builder

```tsx
const StrategyBuilder = () => {
  const [selectedOptions, setSelectedOptions] = useState<OptionContract[]>([]);

  const handleCellClick = (strike: number, expiration: string) => {
    // Custom logic to build multi-leg strategies
    // Add option to selected list
  };

  const calculateCustomMetrics = () => {
    // Calculate metrics for custom multi-leg strategy
    if (selectedOptions.length === 2) {
      return calculateBullCallSpreadMetrics(
        selectedOptions[0],
        selectedOptions[1],
        stockPrice
      );
    }
  };

  return (
    <div>
      <OptionsAnalyzer optionChainData={optionData} />

      {/* Custom metrics calculation */}
      {selectedOptions.length > 0 && (
        <MetricsDisplay {...calculateCustomMetrics()} />
      )}
    </div>
  );
};
```

---

## Metrics Calculation Details

### Short Put (Cash-Secured)

**Calculation:**
```typescript
premium = putBid × 100
collateral = strike × 100
maxProfit = premium
maxLoss = collateral - premium
breakeven = strike - (premium / 100)
ROC = (premium / collateral) × 100
```

**Example:**
- Sell 1 put at $150 strike
- Premium: $5.00 ($500 credit)
- Collateral: $15,000 (cash-secured)
- Max Profit: $500
- Max Loss: $14,500
- Breakeven: $145.00
- ROC: 3.33%

### Long Call

**Calculation:**
```typescript
premium = callAsk × 100
debit = premium
maxProfit = Unlimited
maxLoss = debit
breakeven = strike + (premium / 100)
```

**Example:**
- Buy 1 call at $150 strike
- Premium: $5.25 ($525 debit)
- Max Profit: Unlimited
- Max Loss: $525
- Breakeven: $155.25

---

## Customization

### Change Default Strategy

```tsx
<OptionsAnalyzer
  optionChainData={optionData}
  defaultStrategy="long_call"  // Start with long call selected
/>
```

### Custom Styling

```tsx
<OptionsAnalyzer
  optionChainData={optionData}
  className="my-custom-analyzer"
/>
```

```css
.my-custom-analyzer {
  max-width: 1400px;
  margin: 0 auto;
}

.my-custom-analyzer .strategy-btn {
  background: #custom-color;
}
```

---

## Troubleshooting

### Metrics not calculating
**Problem**: Click on cell, but metrics don't appear.

**Solutions**:
- Ensure option has pricing data (bid/ask)
- Check browser console for errors
- Verify `optionChainData` has proper structure

### Wrong metrics displayed
**Problem**: Metrics don't match expected values.

**Solutions**:
- Check selected strategy matches intention
- Verify option type (call vs put)
- Review pricing data (bid vs ask)

### TypeScript errors
**Problem**: Type errors when using components.

**Solutions**:
```typescript
// Import types properly
import type { OptionChainResponse } from './types/options';
import type { FinancialMetrics } from './types/metrics';

// Ensure data structure matches
const data: OptionChainResponse = await fetchOptions();
```

---

## Advanced Features

### Backend Integration

Save analyzed strategies to backend:

```typescript
const handleMetricsCalculated = async (metrics: FinancialMetrics) => {
  try {
    await axios.post('/api/strategies/save', {
      ticker: optionData.ticker,
      metrics: metrics,
      timestamp: new Date().toISOString(),
      userId: currentUser.id,
    });
  } catch (error) {
    console.error('Failed to save strategy:', error);
  }
};
```

### Real-time Updates

Connect with WebSocket for live pricing:

```typescript
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws/options');

  ws.onmessage = (event) => {
    const updatedData = JSON.parse(event.data);
    setOptionData(updatedData);
  };

  return () => ws.close();
}, []);
```

---

## Performance Tips

1. **Memoization**: Calculator uses `useMemo` for expensive calculations
2. **Lazy Loading**: Only calculate when cell is clicked
3. **Debouncing**: Avoid rapid recalculations
4. **Caching**: Cache frequently used calculations

---

## Next Steps

- [ ] Add multi-leg strategy builder
- [ ] Integrate with BSM pricing model
- [ ] Add profit/loss charts
- [ ] Export analysis to PDF
- [ ] Save strategies to backend
- [ ] Compare multiple strategies side-by-side

---

For more information, see:
- [COMPONENTS.md](./COMPONENTS.md) - Component documentation
- [USAGE_GUIDE.md](./src/USAGE_GUIDE.md) - Quick start guide
- [README.md](./README.md) - Project overview
