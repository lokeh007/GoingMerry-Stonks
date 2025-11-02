

# ProfitLossChart Component - Complete Guide

Professional profit/loss visualization for options strategies using Chart.js.

---

## Overview

The **ProfitLossChart** component displays the characteristic "hockey stick" profit/loss diagram for options strategies at expiration. It provides visual representation of P/L across different stock prices, helping traders understand risk/reward profiles.

## Features

✅ **Interactive Chart** - Hover to see exact P/L at any stock price
✅ **Multiple Strategies** - Supports all basic options strategies
✅ **Breakeven Markers** - Automatically identifies and displays breakeven points
✅ **Color-Coded Zones** - Green for profit, red for loss
✅ **Responsive Design** - Works on all screen sizes
✅ **Detailed Info Panel** - Shows strategy details, max profit/loss, breakevens
✅ **Professional Styling** - Clean, modern design

---

## Installation

Dependencies are already included in `package.json`:
- `chart.js`: ^4.4.1
- `react-chartjs-2`: ^5.2.0

```bash
npm install
```

---

## Basic Usage

### Standalone Component

```tsx
import { ProfitLossChart } from './components';

const MyComponent = () => {
  return (
    <ProfitLossChart
      strategyParams={{
        type: 'short_put',
        strike: 150,
        premium: 5.25,
        currentStockPrice: 155
      }}
    />
  );
};
```

### Integrated with OptionsAnalyzer

The chart is **automatically included** in the `OptionsAnalyzer` component:

```tsx
import { OptionsAnalyzer } from './components';

<OptionsAnalyzer
  optionChainData={optionData}
  defaultStrategy="short_put"
/>
// P/L chart appears automatically when option is selected
```

---

## Strategy Examples

### 1. Short Put (Cash-Secured)

```tsx
<ProfitLossChart
  strategyParams={{
    type: 'short_put',
    strike: 150,
    premium: 5.25,           // Credit received
    currentStockPrice: 155
  }}
/>
```

**Characteristics:**
- Flat profit line above strike (max profit = premium)
- Diagonal loss line below strike (slope = -1)
- Breakeven at strike - premium ($144.75)
- Limited upside, substantial downside

**Visual:**
```
  Profit
    ↑
    |     ──────────────────  (Max profit: $525)
    |    /
    |   /
────|──/─────────────────────→ Stock Price
    | /  BE
    |/
    /    (Max loss increases as stock drops)
```

### 2. Long Call

```tsx
<ProfitLossChart
  strategyParams={{
    type: 'long_call',
    strike: 150,
    premium: -5.25,          // Debit paid (negative)
    currentStockPrice: 155
  }}
/>
```

**Characteristics:**
- Flat loss line below strike (max loss = premium)
- Diagonal profit line above strike (slope = +1)
- Breakeven at strike + premium ($155.25)
- Limited downside, unlimited upside

**Visual:**
```
  Profit
    ↑         /
    |        /
    |       /  (Unlimited profit potential)
    |      /
────|─────/───BE───────────────→ Stock Price
    |    /
    |───────────────  (Max loss: -$525)
```

### 3. Long Put

```tsx
<ProfitLossChart
  strategyParams={{
    type: 'long_put',
    strike: 150,
    premium: -4.75,
    currentStockPrice: 155
  }}
/>
```

**Characteristics:**
- Diagonal profit line below strike (slope = -1)
- Flat loss line above strike (max loss = premium)
- Breakeven at strike - premium ($145.25)
- Profit increases as stock drops

**Visual:**
```
  Profit
    ↑
    |\
    | \
    |  \  (Profit as stock drops)
────|───\──BE───────────────────→ Stock Price
    |    \
    |     ──────────────  (Max loss: -$475)
```

### 4. Short Call (Naked)

```tsx
<ProfitLossChart
  strategyParams={{
    type: 'short_call',
    strike: 150,
    premium: 4.50,
    currentStockPrice: 145
  }}
/>
```

**Characteristics:**
- Flat profit line below strike (max profit = premium)
- Diagonal loss line above strike (slope = -1)
- Breakeven at strike + premium ($154.50)
- Limited upside, unlimited downside (theoretically)

---

## Props API

```typescript
interface ProfitLossChartProps {
  // Required: Strategy parameters
  strategyParams: StrategyParams;

  // Optional display settings
  height?: number;              // Default: 400
  width?: string | number;      // Default: '100%'
  numPoints?: number;           // Default: 100
  priceRange?: number;          // Default: 0.3 (±30%)
  showGrid?: boolean;           // Default: true
  showBreakevens?: boolean;     // Default: true
  title?: string;               // Default: auto-generated
  className?: string;
}
```

### StrategyParams

```typescript
interface StrategyParams {
  type: 'long_call' | 'long_put' | 'short_call' | 'short_put'
        | 'bull_call_spread' | 'bear_put_spread' | 'iron_condor';

  strike: number;               // Primary strike price
  strike2?: number;             // For spreads
  strike3?: number;             // For iron condor
  strike4?: number;             // For iron condor

  premium: number;              // Premium (positive = credit, negative = debit)
  premium2?: number;            // For spreads
  premium3?: number;            // For iron condor
  premium4?: number;            // For iron condor

  currentStockPrice?: number;   // Current stock price (for reference)
}
```

---

## Customization Examples

### Custom Height and Width

```tsx
<ProfitLossChart
  strategyParams={params}
  height={500}
  width="800px"
/>
```

### More Data Points (Smoother Curve)

```tsx
<ProfitLossChart
  strategyParams={params}
  numPoints={200}  // More points = smoother
/>
```

### Wider Price Range

```tsx
<ProfitLossChart
  strategyParams={params}
  priceRange={0.5}  // ±50% from current price
/>
```

### Hide Grid Lines

```tsx
<ProfitLossChart
  strategyParams={params}
  showGrid={false}
/>
```

### Custom Title

```tsx
<ProfitLossChart
  strategyParams={params}
  title="My Custom Strategy P/L"
/>
```

---

## Reading the Chart

### Color Coding

- **Green Zone** (Top): Profit area
- **Red Zone** (Bottom): Loss area
- **Thick Black Line**: Zero profit/loss (breakeven)
- **Blue Line**: P/L curve

### Information Panel

Below the chart, you'll find:

1. **Strategy Details**
   - Strike price
   - Premium paid/received
   - Current stock price

2. **P/L Summary**
   - Max profit
   - Max loss

3. **Breakeven Points**
   - Exact stock prices where P/L = $0

4. **Chart Legend**
   - Color zone explanations

### Tooltips

Hover over any point on the chart to see:
- Exact stock price
- Exact P/L at that price

---

## P/L Calculation Details

### Short Put

```typescript
if (stockPrice >= strike) {
  P/L = premium × 100  // Flat profit
} else {
  P/L = (premium × 100) - ((strike - stockPrice) × 100)
}

Breakeven = strike - premium
```

### Long Call

```typescript
if (stockPrice >= strike) {
  P/L = ((stockPrice - strike) × 100) - (premium × 100)
} else {
  P/L = -(premium × 100)  // Flat loss
}

Breakeven = strike + premium
```

### Long Put

```typescript
if (stockPrice <= strike) {
  P/L = ((strike - stockPrice) × 100) - (premium × 100)
} else {
  P/L = -(premium × 100)  // Flat loss
}

Breakeven = strike - premium
```

### Short Call

```typescript
if (stockPrice <= strike) {
  P/L = premium × 100  // Flat profit
} else {
  P/L = (premium × 100) - ((stockPrice - strike) × 100)
}

Breakeven = strike + premium
```

---

## Advanced Features

### Dynamic Updates

```tsx
const [params, setParams] = useState<StrategyParams>({
  type: 'short_put',
  strike: 150,
  premium: 5.25,
  currentStockPrice: 155
});

// Update based on user selection
const handleStrikeChange = (newStrike: number) => {
  setParams(prev => ({ ...prev, strike: newStrike }));
};

return <ProfitLossChart strategyParams={params} />;
```

### Multi-Strategy Comparison

```tsx
const ComparisonView = () => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
      <ProfitLossChart
        strategyParams={{
          type: 'short_put',
          strike: 150,
          premium: 5.25,
          currentStockPrice: 155
        }}
        title="Short Put"
      />
      <ProfitLossChart
        strategyParams={{
          type: 'long_call',
          strike: 150,
          premium: -5.25,
          currentStockPrice: 155
        }}
        title="Long Call"
      />
    </div>
  );
};
```

---

## Performance Tips

1. **Limit Data Points**: Use 100-150 points for optimal performance
2. **Memoize Parameters**: Use `useMemo` to prevent unnecessary recalculations
3. **Responsive Height**: Let container control height when possible

---

## Troubleshooting

### Chart not displaying

**Problem**: Blank or missing chart

**Solutions**:
- Ensure Chart.js is installed: `npm install chart.js react-chartjs-2`
- Check that parameters are valid numbers
- Verify container has height

### Wrong shape

**Problem**: P/L curve doesn't match expected pattern

**Solutions**:
- Check premium sign (positive = credit, negative = debit)
- Verify strike price is reasonable
- Ensure option type matches intention

### TypeScript errors

**Problem**: Type errors when using component

**Solutions**:
```typescript
import type { StrategyParams } from '../utils/profitLossCalculator';

const params: StrategyParams = {
  type: 'short_put',
  strike: 150,
  premium: 5.25,
  currentStockPrice: 155
};
```

---

## Real-World Example

### Complete Options Analysis Page

```tsx
import React, { useState } from 'react';
import { OptionsAnalyzer, ProfitLossChart } from './components';
import type { StrategyParams } from './utils/profitLossCalculator';

const AnalysisPage = () => {
  const [selectedParams, setSelectedParams] = useState<StrategyParams | null>(null);

  return (
    <div className="analysis-page">
      <h1>AAPL Options Analysis</h1>

      {/* Integrated analyzer with automatic chart */}
      <OptionsAnalyzer
        optionChainData={optionData}
        onMetricsCalculated={(metrics) => {
          // Chart updates automatically
          console.log('Metrics calculated:', metrics);
        }}
      />

      {/* Or standalone chart for comparison */}
      {selectedParams && (
        <div className="comparison-section">
          <h2>Alternative Strategy</h2>
          <ProfitLossChart strategyParams={selectedParams} />
        </div>
      )}
    </div>
  );
};
```

---

## Best Practices

1. **Always show current stock price** - Helps users understand context
2. **Use appropriate price range** - 30% is good default, adjust for volatile stocks
3. **Show breakevens** - Critical for understanding risk
4. **Provide context** - Show max profit/loss in info panel
5. **Keep it simple** - One strategy per chart for clarity

---

## Next Steps

- [ ] Add spread strategies (bull call spread, etc.)
- [ ] Implement multi-leg strategy builder
- [ ] Add probability cones
- [ ] Show time decay (theta) visualization
- [ ] Export chart as image
- [ ] Add historical stock price overlay

---

For more information:
- [COMPONENTS.md](./COMPONENTS.md) - All components
- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Integration details
- [Chart.js Docs](https://www.chartjs.org/docs/latest/)

**Built with Chart.js following SOLID/KISS principles** 📊
