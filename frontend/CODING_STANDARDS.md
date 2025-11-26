# Frontend Coding Standards

## Table of Contents

1. [Null and Undefined Handling](#null-and-undefined-handling)
2. [TypeScript Best Practices](#typescript-best-practices)
3. [React Component Guidelines](#react-component-guidelines)
4. [Testing Requirements](#testing-requirements)
5. [Code Review Checklist](#code-review-checklist)

---

## Null and Undefined Handling

### ⚠️ CRITICAL: Avoid Falsy-Value Bugs

**Problem**: JavaScript treats `0`, `""`, `false`, `null`, and `undefined` as falsy values. This can cause bugs when checking financial data where **zero is often a valid and meaningful value**.

### ❌ Bad - Falsy Value Bug

```typescript
// BUG: When debt_to_equity = 0 (debt-free company), this evaluates to false
const className = stock.debt_to_equity && stock.debt_to_equity < 0.5 ? 'value-good' : '';

// What happens:
// debt_to_equity = 0   → false && true  → false (❌ WRONG!)
// debt_to_equity = null → false && true → false (✅ Correct)
// debt_to_equity = 0.3  → true && true  → true  (✅ Correct)
```

### ✅ Good - Explicit Null Check

```typescript
// CORRECT: Explicitly check for null/undefined
const className = stock.debt_to_equity != null && stock.debt_to_equity < 0.5 ? 'value-good' : '';

// What happens:
// debt_to_equity = 0    → true && true  → true  (✅ Correct!)
// debt_to_equity = null → false && true → false (✅ Correct)
// debt_to_equity = 0.3  → true && true  → true  (✅ Correct)
```

### Rule of Thumb

**Always use explicit null checks when dealing with numeric or boolean data:**

- ✅ `value != null` - Checks for both `null` and `undefined`
- ✅ `value !== undefined` - Checks only for `undefined`
- ✅ `value !== null` - Checks only for `null`
- ❌ `value` - Dangerous! Treats `0`, `false`, `""` as falsy
- ❌ `!!value` - Same issue, avoid for numeric checks

### Financial Data Examples

```typescript
// ✅ CORRECT: Debt-to-Equity Ratio (0 = debt-free, excellent!)
if (stock.debt_to_equity != null && stock.debt_to_equity < 0.5) {
  // Highlight as good
}

// ✅ CORRECT: PEG Ratio (0 = potentially undervalued)
if (stock.peg_ratio != null && stock.peg_ratio < 1) {
  // Highlight as good
}

// ✅ CORRECT: ROE (0 = break-even, valid data point)
if (stock.roe != null && stock.roe > 15) {
  // Highlight as good
}

// ✅ CORRECT: Boolean flags
if (stock.is_profitable === true) {
  // Use explicit boolean check
}
```

### Display Logic

When displaying values, handle null/undefined separately:

```typescript
// ✅ CORRECT
const displayValue = stock.debt_to_equity != null
  ? stock.debt_to_equity.toFixed(2)
  : 'N/A';

// ❌ BAD: Shows 'N/A' for zero values!
const displayValue = stock.debt_to_equity
  ? stock.debt_to_equity.toFixed(2)
  : 'N/A';
```

---

## TypeScript Best Practices

### Type Safety

1. **Always define interfaces for component props and data structures**

```typescript
// ✅ CORRECT
interface StockData {
  ticker: string;
  price?: number;  // Optional
  volume: number;  // Required
}

// ❌ BAD
const stock: any = getData();  // Never use 'any'
```

2. **Use strict TypeScript configuration**

Ensure `tsconfig.json` has:

```json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "noImplicitAny": true
  }
}
```

3. **Prefer type inference over explicit typing when obvious**

```typescript
// ✅ CORRECT
const count = 5;  // TypeScript infers number

// ❌ UNNECESSARY
const count: number = 5;
```

### Optional Chaining and Nullish Coalescing

```typescript
// ✅ CORRECT: Safe property access
const marketCap = stock?.financials?.market_cap ?? 0;

// ✅ CORRECT: Distinguish null/undefined from 0
const price = stock.price ?? 'N/A';  // Only replaces null/undefined, not 0
const price = stock.price || 'N/A';  // ❌ WRONG: Replaces 0 as well!
```

---

## React Component Guidelines

### Component Structure

1. **Separate display components from business logic**

```typescript
// ✅ CORRECT: Pure utility function
// utils/metricsCalculator.ts
export const calculateROE = (netIncome: number, equity: number): number => {
  return (netIncome / equity) * 100;
};

// Component uses utility
const MetricsDisplay: React.FC<Props> = ({ stock }) => {
  const roe = calculateROE(stock.netIncome, stock.equity);
  return <div>{roe.toFixed(2)}%</div>;
};
```

2. **Use controlled components**

```typescript
// ✅ CORRECT
const [ticker, setTicker] = useState('');
<input value={ticker} onChange={(e) => setTicker(e.target.value)} />

// ❌ BAD: Uncontrolled component
<input ref={inputRef} />
```

### Conditional Rendering

```typescript
// ✅ CORRECT: Explicit conditional
{stock.debt_to_equity != null ? (
  <td className={stock.debt_to_equity < 0.5 ? 'good' : ''}>
    {stock.debt_to_equity.toFixed(2)}
  </td>
) : (
  <td>N/A</td>
)}

// ❌ BAD: Relies on falsy values
{stock.debt_to_equity && <td>{stock.debt_to_equity}</td>}
```

---

## Testing Requirements

### Test Coverage Goals

- **Minimum**: 54% (enforced by CI/CD)
- **Target**: 70%+
- **Critical components**: 90%+

### Required Test Cases

For every component that displays financial data, test:

1. ✅ **Zero values** - Ensure `0` is treated as valid data
2. ✅ **Null values** - Ensure proper "N/A" or fallback display
3. ✅ **Threshold boundaries** - Test values at, above, and below thresholds
4. ✅ **Edge cases** - Very large numbers, negative numbers, decimals

### Example Test Structure

```typescript
describe('ScreenerResults - debt_to_equity highlighting', () => {
  it('should apply value-good class when debt_to_equity is 0 (debt-free)', () => {
    // Test the critical zero case
    const mockStock = { debt_to_equity: 0 };
    render(<ScreenerResults stock={mockStock} />);

    const cell = screen.getByTestId('debt-to-equity');
    expect(cell).toHaveClass('value-good');
    expect(cell).toHaveTextContent('0.00');
  });

  it('should NOT apply value-good class when debt_to_equity is null', () => {
    // Test the null case
    const mockStock = { debt_to_equity: null };
    render(<ScreenerResults stock={mockStock} />);

    const cell = screen.getByTestId('debt-to-equity');
    expect(cell).not.toHaveClass('value-good');
    expect(cell).toHaveTextContent('N/A');
  });

  it('should apply value-good class when debt_to_equity is 0.49 (below threshold)', () => {
    // Test boundary case
    const mockStock = { debt_to_equity: 0.49 };
    render(<ScreenerResults stock={mockStock} />);

    const cell = screen.getByTestId('debt-to-equity');
    expect(cell).toHaveClass('value-good');
  });

  it('should NOT apply value-good class when debt_to_equity is 0.5 (at threshold)', () => {
    // Test exact threshold
    const mockStock = { debt_to_equity: 0.5 };
    render(<ScreenerResults stock={mockStock} />);

    const cell = screen.getByTestId('debt-to-equity');
    expect(cell).not.toHaveClass('value-good');
  });
});
```

### Testing Commands

```bash
# Run all tests
npm test

# Run specific test file
npm test -- --testPathPattern=ScreenerResults

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

---

## Code Review Checklist

### Before Submitting a PR

- [ ] All tests pass (`npm test`)
- [ ] TypeScript compilation succeeds (`npm run type-check`)
- [ ] ESLint passes (`npm run lint`)
- [ ] Code coverage meets minimum threshold (54%)
- [ ] No console.log or debugger statements
- [ ] Props and data structures have TypeScript interfaces

### Null/Undefined Checks

- [ ] All numeric comparisons use explicit null checks (`!= null`)
- [ ] All boolean conditionals use explicit comparisons (`=== true`)
- [ ] Display logic handles null/undefined separately from zero/false
- [ ] Optional chaining (`?.`) is used for nested property access

### Financial Data Specific

- [ ] Zero values are treated as valid data (not falsy)
- [ ] Negative numbers are handled correctly (e.g., negative earnings)
- [ ] Percentage values are formatted consistently (`toFixed(1)%`)
- [ ] Currency values are formatted consistently (`$X.XXB`, `$X.XXM`)
- [ ] Very large numbers (billions) are displayed readably

### Testing

- [ ] Tests include zero-value cases
- [ ] Tests include null/undefined cases
- [ ] Tests include boundary/threshold cases
- [ ] Tests verify CSS class application
- [ ] Tests verify display text (including 'N/A')

### Component Quality

- [ ] Components are pure and reusable
- [ ] Business logic is in utility functions, not components
- [ ] State management is clear and minimal
- [ ] No unnecessary re-renders

---

## ESLint Configuration

The project uses custom ESLint rules to catch common bugs:

```json
{
  "rules": {
    "eqeqeq": ["error", "always", { "null": "ignore" }],
    "@typescript-eslint/strict-boolean-expressions": ["warn", {
      "allowString": false,
      "allowNumber": false,
      "allowNullableObject": false
    }],
    "no-extra-boolean-cast": "error",
    "no-constant-condition": "warn"
  }
}
```

**Key Rules:**
- `eqeqeq`: Enforces `===` and `!==` (allows `== null` for null/undefined check)
- `strict-boolean-expressions`: Warns about non-boolean values in conditionals
- `no-extra-boolean-cast`: Prevents unnecessary `!!` casts

---

## Common Pitfalls to Avoid

### 1. Falsy Value Assumptions

```typescript
// ❌ BAD: Assumes 0 is invalid
if (value && value > threshold) { }

// ✅ GOOD: Explicit null check
if (value != null && value > threshold) { }
```

### 2. Boolean Coercion

```typescript
// ❌ BAD: Treats 0, "", null as false
const isValid = !!stock.price;

// ✅ GOOD: Explicit check
const isValid = stock.price != null;
```

### 3. OR Operator for Defaults

```typescript
// ❌ BAD: Replaces 0 with default
const price = stock.price || 'N/A';  // 0 becomes 'N/A'!

// ✅ GOOD: Only replaces null/undefined
const price = stock.price ?? 'N/A';  // 0 stays as 0
```

### 4. Nested Property Access

```typescript
// ❌ BAD: Can throw error
const market_cap = stock.financials.market_cap;

// ✅ GOOD: Safe access
const market_cap = stock?.financials?.market_cap ?? null;
```

---

## Resources

- [TypeScript Handbook - Strictness](https://www.typescriptlang.org/docs/handbook/2/basic-types.html#strictness)
- [React Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [JavaScript Equality Table](https://dorey.github.io/JavaScript-Equality-Table/)
- [MDN: Nullish Coalescing Operator](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing)

---

**Last Updated**: November 26, 2025
**Maintainers**: GoingMerry-Stonks Team
