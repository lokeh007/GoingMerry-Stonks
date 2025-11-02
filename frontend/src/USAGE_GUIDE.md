# MetricsDisplay Component - Quick Start Guide

## Installation

The component is already included in the project. No additional installation needed.

## Quick Start

### 1. Basic Import and Usage

```tsx
import React from 'react';
import MetricsDisplay from './components/MetricsDisplay';

const MyComponent = () => {
  return (
    <MetricsDisplay
      netCredit={250}
      maxProfit={250}
      maxLoss={-750}
      breakeven={[148.5, 151.5]}
      collateral={1000}
    />
  );
};

export default MyComponent;
```

### 2. With Dynamic Data

```tsx
import React, { useState, useEffect } from 'react';
import MetricsDisplay from './components/MetricsDisplay';

const StrategyAnalyzer = () => {
  const [metrics, setMetrics] = useState({
    netCredit: null,
    maxProfit: null,
    maxLoss: null,
    breakeven: null,
    collateral: null,
  });

  useEffect(() => {
    // Fetch or calculate metrics
    const calculatedMetrics = calculateStrategyMetrics();
    setMetrics(calculatedMetrics);
  }, []);

  return (
    <div>
      <h1>Iron Condor Strategy</h1>
      <MetricsDisplay
        netCredit={metrics.netCredit}
        maxProfit={metrics.maxProfit}
        maxLoss={metrics.maxLoss}
        breakeven={metrics.breakeven}
        collateral={metrics.collateral}
        title="Iron Condor Metrics"
      />
    </div>
  );
};
```

### 3. Add to Your App.tsx

```tsx
import React, { useState } from 'react';
import OptionsGrid from './components/OptionsGrid';
import MetricsDisplay from './components/MetricsDisplay';
import './App.css';

const App = () => {
  const [optionData, setOptionData] = useState(null);

  // Sample metrics for demonstration
  const sampleMetrics = {
    netCredit: 250,
    maxProfit: 250,
    maxLoss: -750,
    breakeven: [148.5, 151.5],
    collateral: 1000,
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>GoingMerry-Stonks</h1>
      </header>

      <main className="app-main">
        {/* Metrics Display Section */}
        <section className="metrics-section">
          <MetricsDisplay {...sampleMetrics} />
        </section>

        {/* Options Grid Section */}
        <section className="grid-section">
          {optionData && <OptionsGrid gridData={optionData} />}
        </section>
      </main>
    </div>
  );
};

export default App;
```

## Common Use Cases

### Iron Condor Strategy

```tsx
<MetricsDisplay
  title="Iron Condor"
  netCredit={250}          // Credit received
  maxProfit={250}          // Credit is max profit
  maxLoss={-750}          // Spread width - credit
  breakeven={[148.5, 151.5]}  // Two breakeven points
  collateral={1000}        // Short put spread width
/>
```

### Long Call (Debit Strategy)

```tsx
<MetricsDisplay
  title="Long Call"
  netCredit={-525}         // Debit paid (negative)
  maxProfit={null}         // Unlimited upside
  maxLoss={-525}          // Premium paid
  breakeven={155.25}       // Single breakeven
  collateral={525}         // Premium paid
/>
```

### Covered Call

```tsx
<MetricsDisplay
  title="Covered Call"
  netCredit={450}          // Premium received
  maxProfit={950}          // Strike - stock cost + premium
  maxLoss={-14550}        // Stock cost - premium
  breakeven={149.55}       // Stock cost - premium
  collateral={15000}       // Stock value
/>
```

### Bull Put Spread

```tsx
<MetricsDisplay
  title="Bull Put Spread"
  netCredit={150}
  maxProfit={150}
  maxLoss={-350}
  breakeven={148.5}
  collateral={500}
/>
```

## Customization Options

### Custom Title and Format

```tsx
<MetricsDisplay
  netCredit={250}
  maxProfit={250}
  maxLoss={-750}
  breakeven={150}
  collateral={1000}
  title="My Custom Strategy"
  format={{
    showPercentages: true,      // Show ROC %
    currencyDecimals: 2,        // $250.00
    percentageDecimals: 2,      // 25.00%
    compact: false,             // Use compact mode
  }}
/>
```

### Compact Mode

```tsx
<MetricsDisplay
  {...metrics}
  format={{ compact: true }}
  className="compact-metrics"
/>
```

### Custom Styling

```tsx
// In your component
<MetricsDisplay
  {...metrics}
  className="my-custom-class"
/>

// In your CSS file
.my-custom-class {
  max-width: 800px;
  margin: 20px auto;
}

.my-custom-class .metric-card {
  background: linear-gradient(135deg, #f5f5f5, #e0e0e0);
}
```

## Integration with Backend API

```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import MetricsDisplay from './components/MetricsDisplay';

const StrategyBuilder = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculateMetrics = async (strategy) => {
    setLoading(true);
    try {
      // Call your backend endpoint
      const response = await axios.post('/api/calculate-metrics', {
        strategy: strategy,
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Error calculating metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Calculating...</div>;
  if (!metrics) return <div>Select a strategy</div>;

  return (
    <MetricsDisplay
      netCredit={metrics.netCredit}
      maxProfit={metrics.maxProfit}
      maxLoss={metrics.maxLoss}
      breakeven={metrics.breakeven}
      collateral={metrics.collateral}
    />
  );
};
```

## TypeScript Types

```typescript
import type { FinancialMetrics } from './types/metrics';

// Define your metrics with proper types
const metrics: FinancialMetrics = {
  netCredit: 250,
  maxProfit: 250,
  maxLoss: -750,
  breakeven: [148.5, 151.5],
  collateral: 1000,
};

// Use in component
<MetricsDisplay {...metrics} />
```

## Running the Example

To see the MetricsExample component in action:

```tsx
// In App.tsx
import MetricsExample from './components/MetricsExample';

function App() {
  return (
    <div className="app">
      <MetricsExample />
    </div>
  );
}
```

Then start the dev server:

```bash
cd frontend
npm start
```

Visit: http://localhost:3000

## Troubleshooting

### Component not rendering
- Check that all props are provided
- Ensure values are `number | null`, not `undefined`
- Check browser console for errors

### Styling issues
- Make sure CSS is imported: `import '../styles/MetricsDisplay.css'`
- Check for CSS conflicts
- Try adding `!important` to custom styles

### TypeScript errors
- Import types: `import type { FinancialMetrics } from './types/metrics'`
- Ensure null handling: `value ?? null`
- Check prop types match interface

## Next Steps

1. **Integrate with OptionsGrid**: Select cells to build strategies
2. **Add BSM Calculator**: Calculate theoretical prices
3. **Create Strategy Builder**: Multi-leg position builder
4. **Add Charts**: Profit/loss diagrams
5. **Real-time Updates**: WebSocket integration

## Support

For issues or questions:
- Check [COMPONENTS.md](./COMPONENTS.md) for detailed documentation
- Review example code in `MetricsExample.tsx`
- Check TypeScript interfaces in `types/metrics.ts`

---

Happy coding! 🚀
