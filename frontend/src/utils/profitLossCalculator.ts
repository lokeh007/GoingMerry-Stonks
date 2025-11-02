/**
 * Profit/Loss Calculator Utility
 *
 * Calculates P/L values at different stock prices for various options strategies.
 * Used to generate data points for P/L charts.
 */

/**
 * Strategy parameters for P/L calculation
 */
export interface StrategyParams {
  /**
   * Strategy type
   */
  type: 'long_call' | 'long_put' | 'short_call' | 'short_put' | 'bull_call_spread' | 'bear_put_spread' | 'iron_condor';

  /**
   * Strike price(s)
   */
  strike: number;
  strike2?: number; // For spreads
  strike3?: number; // For iron condor
  strike4?: number; // For iron condor

  /**
   * Premium(s) - positive for credit, negative for debit
   */
  premium: number;
  premium2?: number; // For spreads
  premium3?: number; // For iron condor
  premium4?: number; // For iron condor

  /**
   * Current stock price (optional, for reference line)
   */
  currentStockPrice?: number;
}

/**
 * P/L data point
 */
export interface PLDataPoint {
  stockPrice: number;
  profitLoss: number;
}

/**
 * Calculate profit/loss for a long call at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param strike - Strike price
 * @param premium - Premium paid
 * @returns Profit/Loss value
 */
export const calculateLongCallPL = (
  stockPrice: number,
  strike: number,
  premium: number
): number => {
  const intrinsicValue = Math.max(0, stockPrice - strike);
  const contractValue = intrinsicValue * 100;
  const cost = premium * 100;
  return contractValue - cost;
};

/**
 * Calculate profit/loss for a long put at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param strike - Strike price
 * @param premium - Premium paid
 * @returns Profit/Loss value
 */
export const calculateLongPutPL = (
  stockPrice: number,
  strike: number,
  premium: number
): number => {
  const intrinsicValue = Math.max(0, strike - stockPrice);
  const contractValue = intrinsicValue * 100;
  const cost = premium * 100;
  return contractValue - cost;
};

/**
 * Calculate profit/loss for a short call at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param strike - Strike price
 * @param premium - Premium received
 * @returns Profit/Loss value
 */
export const calculateShortCallPL = (
  stockPrice: number,
  strike: number,
  premium: number
): number => {
  const intrinsicValue = Math.max(0, stockPrice - strike);
  const loss = intrinsicValue * 100;
  const credit = premium * 100;
  return credit - loss;
};

/**
 * Calculate profit/loss for a short put at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param strike - Strike price
 * @param premium - Premium received
 * @returns Profit/Loss value
 */
export const calculateShortPutPL = (
  stockPrice: number,
  strike: number,
  premium: number
): number => {
  const intrinsicValue = Math.max(0, strike - stockPrice);
  const loss = intrinsicValue * 100;
  const credit = premium * 100;
  return credit - loss;
};

/**
 * Calculate profit/loss for a bull call spread at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param longStrike - Lower strike (bought call)
 * @param shortStrike - Higher strike (sold call)
 * @param longPremium - Premium paid for long call
 * @param shortPremium - Premium received for short call
 * @returns Profit/Loss value
 */
export const calculateBullCallSpreadPL = (
  stockPrice: number,
  longStrike: number,
  shortStrike: number,
  longPremium: number,
  shortPremium: number
): number => {
  const longCallPL = calculateLongCallPL(stockPrice, longStrike, longPremium);
  const shortCallPL = calculateShortCallPL(stockPrice, shortStrike, shortPremium);
  return longCallPL + shortCallPL;
};

/**
 * Calculate profit/loss for a bear put spread at expiration
 *
 * @param stockPrice - Stock price at expiration
 * @param longStrike - Higher strike (bought put)
 * @param shortStrike - Lower strike (sold put)
 * @param longPremium - Premium paid for long put
 * @param shortPremium - Premium received for short put
 * @returns Profit/Loss value
 */
export const calculateBearPutSpreadPL = (
  stockPrice: number,
  longStrike: number,
  shortStrike: number,
  longPremium: number,
  shortPremium: number
): number => {
  const longPutPL = calculateLongPutPL(stockPrice, longStrike, longPremium);
  const shortPutPL = calculateShortPutPL(stockPrice, shortStrike, shortPremium);
  return longPutPL + shortPutPL;
};

/**
 * Generate P/L data points for a strategy across a range of stock prices
 *
 * @param params - Strategy parameters
 * @param numPoints - Number of data points to generate (default: 100)
 * @param priceRange - Price range multiplier (default: 0.3 = ±30%)
 * @returns Array of P/L data points
 */
export const generatePLData = (
  params: StrategyParams,
  numPoints: number = 100,
  priceRange: number = 0.3
): PLDataPoint[] => {
  const { type, strike, strike2, premium, premium2, currentStockPrice } = params;

  // Determine the center price for the range
  const centerPrice = currentStockPrice || strike;

  // Calculate price range
  const minPrice = centerPrice * (1 - priceRange);
  const maxPrice = centerPrice * (1 + priceRange);
  const priceStep = (maxPrice - minPrice) / (numPoints - 1);

  const dataPoints: PLDataPoint[] = [];

  for (let i = 0; i < numPoints; i++) {
    const stockPrice = minPrice + (i * priceStep);
    let profitLoss = 0;

    switch (type) {
      case 'long_call':
        profitLoss = calculateLongCallPL(stockPrice, strike, premium);
        break;

      case 'long_put':
        profitLoss = calculateLongPutPL(stockPrice, strike, premium);
        break;

      case 'short_call':
        profitLoss = calculateShortCallPL(stockPrice, strike, premium);
        break;

      case 'short_put':
        profitLoss = calculateShortPutPL(stockPrice, strike, premium);
        break;

      case 'bull_call_spread':
        if (strike2 !== undefined && premium2 !== undefined) {
          profitLoss = calculateBullCallSpreadPL(
            stockPrice,
            strike,
            strike2,
            premium,
            premium2
          );
        }
        break;

      case 'bear_put_spread':
        if (strike2 !== undefined && premium2 !== undefined) {
          profitLoss = calculateBearPutSpreadPL(
            stockPrice,
            strike,
            strike2,
            premium,
            premium2
          );
        }
        break;

      default:
        profitLoss = 0;
    }

    dataPoints.push({
      stockPrice: Math.round(stockPrice * 100) / 100,
      profitLoss: Math.round(profitLoss * 100) / 100,
    });
  }

  return dataPoints;
};

/**
 * Find breakeven points in P/L data
 *
 * @param dataPoints - Array of P/L data points
 * @returns Array of breakeven stock prices
 */
export const findBreakevens = (dataPoints: PLDataPoint[]): number[] => {
  const breakevens: number[] = [];

  for (let i = 1; i < dataPoints.length; i++) {
    const prev = dataPoints[i - 1];
    const curr = dataPoints[i];

    // Check if P/L crosses zero
    if ((prev.profitLoss < 0 && curr.profitLoss >= 0) ||
        (prev.profitLoss > 0 && curr.profitLoss <= 0)) {
      // Linear interpolation to find exact breakeven
      const slope = (curr.profitLoss - prev.profitLoss) / (curr.stockPrice - prev.stockPrice);
      const breakeven = prev.stockPrice - (prev.profitLoss / slope);
      breakevens.push(Math.round(breakeven * 100) / 100);
    }
  }

  return breakevens;
};

/**
 * Get strategy display name
 *
 * @param type - Strategy type
 * @returns Human-readable strategy name
 */
export const getStrategyDisplayName = (type: StrategyParams['type']): string => {
  const names: Record<StrategyParams['type'], string> = {
    long_call: 'Long Call',
    long_put: 'Long Put',
    short_call: 'Short Call',
    short_put: 'Short Put (Cash-Secured)',
    bull_call_spread: 'Bull Call Spread',
    bear_put_spread: 'Bear Put Spread',
    iron_condor: 'Iron Condor',
  };

  return names[type] || type;
};

/**
 * Format currency for display
 *
 * @param value - Dollar value
 * @returns Formatted string
 */
export const formatPLCurrency = (value: number): string => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${value.toFixed(0)}`;
};
