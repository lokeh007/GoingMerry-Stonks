# GoingMerry-Stonks Components Documentation

Comprehensive documentation for all React components in the platform.

---

## MetricsDisplay Component

### Overview

The `MetricsDisplay` component renders financial metrics for options positions and strategies in a professional, card-based layout with color-coded values and calculated ratios.

### Location
- **Component**: `src/components/MetricsDisplay.tsx`
- **Styles**: `src/styles/MetricsDisplay.css`
- **Types**: `src/types/metrics.ts`

### Features

- ✅ Card-based responsive grid layout
- ✅ Color-coded values (green for profits, red for losses)
- ✅ Automatic calculation of ROC and Risk/Reward ratio
- ✅ Support for single or multiple breakeven points
- ✅ Credit/Debit position type indicator
- ✅ Formatted currency and percentage display
- ✅ Responsive design (mobile-friendly)
- ✅ Print-optimized styles
- ✅ Smooth animations and hover effects
- ✅ Dark mode support (optional)

### Props

```typescript
interface MetricsDisplayProps {
  netCredit: number | null;        // Required: Net credit received or debit paid
  maxProfit: number | null;        // Required: Maximum profit potential
  maxLoss: number | null;          // Required: Maximum loss potential
  breakeven: number | number[] | null;  // Required: Breakeven price(s)
  collateral: number | null;       // Required: Margin requirement
  format?: MetricsDisplayFormat;   // Optional: Display format options
  title?: string;                  // Optional: Custom title (default: "Position Metrics")
  className?: string;              // Optional: Additional CSS classes
}
```

### Format Options

```typescript
interface MetricsDisplayFormat {
  showPercentages?: boolean;       // Show ROC and percentage values (default: true)
  currencyDecimals?: number;       // Currency decimal places (default: 2)
  percentageDecimals?: number;     // Percentage decimal places (default: 2)
  compact?: boolean;               // Use compact mode (default: false)
}
```

### Basic Usage

```tsx
import { MetricsDisplay } from './components';

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
```

### Advanced Usage

```tsx
import { MetricsDisplay } from './components';

const StrategyAnalysis = () => {
  const metrics = {
    netCredit: 250,
    maxProfit: 250,
    maxLoss: -750,
    breakeven: [148.5, 151.5],
    collateral: 1000,
  };

  const handleMetricsCalculation = () => {
    // Your custom logic here
  };

  return (
    <div>
      <MetricsDisplay
        {...metrics}
        title="Iron Condor Strategy"
        format={{
          showPercentages: true,
          currencyDecimals: 2,
          percentageDecimals: 2,
          compact: false,
        }}
        className="custom-metrics"
      />
    </div>
  );
};
```

### Calculated Metrics

The component automatically calculates:

#### Return on Capital (ROC)
```typescript
ROC = (maxProfit / collateral) * 100
```

#### Risk/Reward Ratio
```typescript
Risk/Reward = |maxLoss| / maxProfit
```

### Metric Cards

The component displays 6 metric cards:

1. **Net Credit/Debit** 💰
   - Shows initial cash flow
   - Green for credit, blue indicator for type

2. **Max Profit** 📈
   - Maximum profit potential
   - Shows ROC percentage
   - Green highlight

3. **Max Loss** 📉
   - Worst-case scenario
   - Shows percentage of collateral
   - Red highlight

4. **Breakeven** ⚖️
   - Break-even price point(s)
   - Supports multiple values

5. **Collateral** 🔒
   - Margin requirement
   - Neutral color

6. **Risk/Reward** ⚡
   - Ratio display (e.g., "3:1")
   - Lower is better

### Examples by Strategy Type

#### Iron Condor (Credit Spread)
```tsx
<MetricsDisplay
  netCredit={250}
  maxProfit={250}
  maxLoss={-750}
  breakeven={[148.5, 151.5]}
  collateral={1000}
  title="Iron Condor"
/>
// Shows: 25% ROC, 3:1 Risk/Reward
```

#### Long Call (Debit)
```tsx
<MetricsDisplay
  netCredit={-525}
  maxProfit={null}  // Unlimited
  maxLoss={-525}
  breakeven={155.25}
  collateral={525}
  title="Long Call"
/>
```

#### Bull Put Spread (Credit)
```tsx
<MetricsDisplay
  netCredit={150}
  maxProfit={150}
  maxLoss={-350}
  breakeven={148.5}
  collateral={500}
  title="Bull Put Spread"
/>
// Shows: 30% ROC, 2.33:1 Risk/Reward
```

### Styling Customization

#### Using className
```tsx
<MetricsDisplay
  {...metrics}
  className="my-custom-metrics"
/>
```

#### Custom CSS
```css
.my-custom-metrics {
  max-width: 900px;
}

.my-custom-metrics .metric-card {
  border-radius: 6px;
}

.my-custom-metrics .metric-value {
  font-size: 32px;
}
```

### Responsive Breakpoints

- **Desktop** (>1024px): 3 columns grid
- **Tablet** (768px-1024px): 2 columns grid
- **Mobile** (<768px): 1 column stack
- **Small Mobile** (<480px): Compact sizes

### Color Coding

The component uses semantic colors:

- **Green (#2e7d32)**: Positive values (profits, credits)
- **Red (#c62828)**: Negative values (losses, debits)
- **Gray (#424242)**: Neutral values (collateral, breakeven)

### Accessibility

- Semantic HTML structure
- Proper heading hierarchy
- Keyboard navigation support
- High contrast colors
- Print-friendly styles

### Performance Considerations

- Uses `useMemo` for calculated values
- Minimal re-renders
- CSS animations use GPU acceleration
- Lazy calculation of derived metrics

### Testing

```tsx
import { render, screen } from '@testing-library/react';
import { MetricsDisplay } from './MetricsDisplay';

test('renders metrics correctly', () => {
  render(
    <MetricsDisplay
      netCredit={250}
      maxProfit={250}
      maxLoss={-750}
      breakeven={150}
      collateral={1000}
    />
  );

  expect(screen.getByText(/Net Credit/i)).toBeInTheDocument();
  expect(screen.getByText(/\$250/i)).toBeInTheDocument();
});
```

---

## OptionsGrid Component

### Overview

Displays option chain data in a table format with strikes as rows and expiration dates as columns.

### Location
- **Component**: `src/components/OptionsGrid.tsx`
- **Styles**: `src/styles/OptionsGrid.css`
- **Types**: `src/types/options.ts`

### Basic Usage

```tsx
import { OptionsGrid } from './components';

const OptionsView = ({ optionChainData }) => {
  return (
    <OptionsGrid
      gridData={optionChainData}
      onCellClick={(strike, expiration) => {
        console.log(`Clicked: ${strike} @ ${expiration}`);
      }}
      showStockPrice={true}
    />
  );
};
```

### Props

```typescript
interface OptionsGridProps {
  gridData: OptionChainResponse;   // Required: Option chain data from API
  onCellClick?: (strike: number, expiration: string) => void;  // Optional
  className?: string;              // Optional
  showStockPrice?: boolean;        // Optional (default: true)
}
```

---

## Integration Examples

### Complete Strategy Analysis Page

```tsx
import React, { useState, useEffect } from 'react';
import { OptionsGrid, MetricsDisplay } from './components';
import axios from 'axios';

const StrategyPage = () => {
  const [optionData, setOptionData] = useState(null);
  const [selectedMetrics, setSelectedMetrics] = useState({
    netCredit: 250,
    maxProfit: 250,
    maxLoss: -750,
    breakeven: [148.5, 151.5],
    collateral: 1000,
  });

  useEffect(() => {
    axios.get('/options/AAPL').then(res => setOptionData(res.data));
  }, []);

  return (
    <div className="strategy-page">
      <h1>Options Strategy Builder</h1>

      {/* Metrics Display */}
      <MetricsDisplay {...selectedMetrics} />

      {/* Options Grid */}
      {optionData && (
        <OptionsGrid
          gridData={optionData}
          onCellClick={(strike, expiration) => {
            // Update metrics based on selected options
            calculateMetrics(strike, expiration);
          }}
        />
      )}
    </div>
  );
};
```

---

## Best Practices

### Type Safety
```typescript
// Always use proper types
import type { FinancialMetrics } from '../types/metrics';

const metrics: FinancialMetrics = {
  netCredit: 250,
  maxProfit: 250,
  maxLoss: -750,
  breakeven: [148.5, 151.5],
  collateral: 1000,
};
```

### Null Handling
```typescript
// Component handles null values gracefully
<MetricsDisplay
  netCredit={data?.netCredit ?? null}
  maxProfit={data?.maxProfit ?? null}
  // ...
/>
```

### Performance
```typescript
// Memoize expensive calculations
const metrics = useMemo(() =>
  calculateStrategyMetrics(positions),
  [positions]
);
```

---

## Troubleshooting

### Metrics not displaying
- Ensure all required props are provided
- Check that values are numbers or null (not undefined)

### Styling conflicts
- Use `className` prop for custom styling
- Check CSS specificity
- Ensure styles are imported

### Type errors
- Import types from `../types/metrics`
- Use proper TypeScript interfaces
- Check null handling

---

## Future Enhancements

- [ ] Add profit/loss chart visualization
- [ ] Support for multi-leg strategies
- [ ] Real-time Greeks integration
- [ ] Strategy comparison mode
- [ ] Export to PDF/CSV
- [ ] Mobile app version
- [ ] WebSocket live updates

---

For more information, see the main [README.md](./README.md)
