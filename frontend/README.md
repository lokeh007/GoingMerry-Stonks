# GoingMerry-Stonks Frontend

React-based frontend for the Stock and Options Analysis Platform.

## Features

- **OptionsGrid Component**: Professional grid/table display for option chains
- **TypeScript**: Full type safety across the application
- **Responsive Design**: Mobile-friendly and print-optimized
- **Real-time Data**: Fetches live option chain data from backend API

## Prerequisites

- Node.js 16+ and npm
- Backend API running on http://localhost:8000

## Installation

```bash
# Install dependencies
npm install
```

## Development

```bash
# Start development server (runs on http://localhost:3000)
npm start

# Build for production
npm run build

# Run tests
npm test
```

## Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/
│   │   └── OptionsGrid.tsx # Main options grid component
│   ├── styles/
│   │   └── OptionsGrid.css # Grid component styles
│   ├── types/
│   │   └── options.ts      # TypeScript interfaces
│   ├── utils/
│   │   └── optionsDataTransform.ts  # Data transformation utilities
│   ├── App.tsx             # Main app component
│   ├── App.css             # App styles
│   ├── index.tsx           # Entry point
│   └── index.css           # Global styles
├── package.json
└── tsconfig.json
```

## Component Usage

### OptionsGrid

The `OptionsGrid` component displays option chain data in a table format:

```tsx
import OptionsGrid from './components/OptionsGrid';
import { OptionChainResponse } from './types/options';

const MyComponent = () => {
  const [data, setData] = useState<OptionChainResponse | null>(null);

  return (
    <OptionsGrid
      gridData={data}
      onCellClick={(strike, expiration) => {
        console.log(`Clicked: ${strike} @ ${expiration}`);
      }}
      showStockPrice={true}
    />
  );
};
```

### Props

- `gridData` (required): Option chain data from API
- `onCellClick` (optional): Callback when a cell is clicked
- `showStockPrice` (optional): Display stock price in header (default: true)
- `className` (optional): Additional CSS classes

## API Integration

The frontend is configured to proxy requests to the backend:

```typescript
// Fetches from http://localhost:8000/options/AAPL
const response = await axios.get('/options/AAPL');
```

## Styling

The grid uses color coding to indicate option moneyness:

- 🟢 **Green** (ITM): In-the-money (strike < stock price)
- 🟡 **Orange** (ATM): At-the-money (within 2% of stock price)
- ⚪ **White** (OTM): Out-of-the-money (strike > stock price)

## Type Safety

All components use TypeScript with strict mode enabled for maximum type safety:

```typescript
interface OptionContract {
  ticker: string;
  strike: number;
  expiration_date: string;
  option_type: 'call' | 'put';
  bid?: number;
  ask?: number;
  // ... more fields
}
```

## License

MIT
