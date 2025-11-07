/**
 * Metrics Calculator Utility
 *
 * Functions to calculate financial metrics for options strategies
 * based on selected option contracts.
 */

import { OptionContract } from '../types/options';
import { FinancialMetrics } from '../types/metrics';

/**
 * Strategy type for metric calculation
 */
export enum StrategyType {
  LONG_CALL = 'long_call',
  LONG_PUT = 'long_put',
  SHORT_CALL = 'short_call',
  SHORT_PUT = 'short_put',
  BULL_CALL_SPREAD = 'bull_call_spread',
  BEAR_PUT_SPREAD = 'bear_put_spread',
  IRON_CONDOR = 'iron_condor',
}

/**
 * Calculate metrics for a long call option
 *
 * @param call - Call option contract
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateLongCallMetrics = (
  call: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  // For long call, we pay the ask price (or use last price as fallback)
  const premium = call.ask || call.last_price || 0;
  const debit = premium * 100; // Options are for 100 shares

  return {
    netCredit: -debit, // Negative because we pay
    maxProfit: null, // Unlimited upside
    maxLoss: -debit, // Limited to premium paid
    breakeven: call.strike + premium, // Strike + premium
    collateral: debit, // Premium paid
    returnOnCapital: null, // Can't calculate for unlimited profit
    riskRewardRatio: null, // Can't calculate for unlimited profit
  };
};

/**
 * Calculate metrics for a long put option
 *
 * @param put - Put option contract
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateLongPutMetrics = (
  put: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  const premium = put.ask || put.last_price || 0;
  const debit = premium * 100;

  // Max profit is if stock goes to $0
  const maxProfit = (put.strike * 100) - debit;

  return {
    netCredit: -debit,
    maxProfit: maxProfit,
    maxLoss: -debit,
    breakeven: put.strike - premium,
    collateral: debit,
    returnOnCapital: (maxProfit / debit) * 100,
    riskRewardRatio: debit / maxProfit,
  };
};

/**
 * Calculate metrics for a short call option (naked)
 *
 * @param call - Call option contract
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateShortCallMetrics = (
  call: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  // For short call, we receive the bid price
  const premium = call.bid || call.last_price || 0;
  const credit = premium * 100;

  // Margin requirement for naked short call (example: 20% of stock value + premium)
  const marginRequirement = (stockPrice * 100 * 0.20) + credit;

  return {
    netCredit: credit,
    maxProfit: credit, // Limited to premium received
    maxLoss: null, // Unlimited risk (theoretically)
    breakeven: call.strike + premium,
    collateral: marginRequirement,
    returnOnCapital: (credit / marginRequirement) * 100,
    riskRewardRatio: null, // Undefined for unlimited risk
  };
};

/**
 * Calculate metrics for a short put option (cash-secured)
 *
 * @param put - Put option contract
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateShortPutMetrics = (
  put: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  const premium = put.bid || put.last_price || 0;
  const credit = premium * 100;

  // Cash-secured: need full strike price in cash
  const collateral = put.strike * 100;
  const maxLoss = collateral - credit; // If stock goes to $0

  return {
    netCredit: credit,
    maxProfit: credit,
    maxLoss: -maxLoss,
    breakeven: put.strike - premium,
    collateral: collateral,
    returnOnCapital: (credit / collateral) * 100,
    riskRewardRatio: maxLoss / credit,
  };
};

/**
 * Calculate metrics for a bull call spread
 *
 * @param longCall - Lower strike (bought) call
 * @param shortCall - Higher strike (sold) call
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateBullCallSpreadMetrics = (
  longCall: OptionContract,
  shortCall: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  const longPremium = longCall.ask || longCall.last_price || 0;
  const shortPremium = shortCall.bid || shortCall.last_price || 0;

  const debit = (longPremium - shortPremium) * 100;
  const spreadWidth = (shortCall.strike - longCall.strike) * 100;
  const maxProfit = spreadWidth - debit;

  return {
    netCredit: -debit,
    maxProfit: maxProfit,
    maxLoss: -debit,
    breakeven: longCall.strike + (debit / 100),
    collateral: debit,
    returnOnCapital: (maxProfit / debit) * 100,
    riskRewardRatio: debit / maxProfit,
  };
};

/**
 * Calculate metrics for a bear put spread
 *
 * @param longPut - Higher strike (bought) put
 * @param shortPut - Lower strike (sold) put
 * @param stockPrice - Current stock price
 * @returns Financial metrics for the position
 */
export const calculateBearPutSpreadMetrics = (
  longPut: OptionContract,
  shortPut: OptionContract,
  stockPrice: number
): FinancialMetrics => {
  const longPremium = longPut.ask || longPut.last_price || 0;
  const shortPremium = shortPut.bid || shortPut.last_price || 0;

  const debit = (longPremium - shortPremium) * 100;
  const spreadWidth = (longPut.strike - shortPut.strike) * 100;
  const maxProfit = spreadWidth - debit;

  return {
    netCredit: -debit,
    maxProfit: maxProfit,
    maxLoss: -debit,
    breakeven: longPut.strike - (debit / 100),
    collateral: debit,
    returnOnCapital: (maxProfit / debit) * 100,
    riskRewardRatio: debit / maxProfit,
  };
};

/**
 * Calculate metrics for a simple single-option position
 * Determines whether it's a call or put, long or short based on available data
 *
 * @param option - Option contract
 * @param stockPrice - Current stock price
 * @param isLong - Whether this is a long position (default: true)
 * @returns Financial metrics for the position
 */
export const calculateSingleOptionMetrics = (
  option: OptionContract,
  stockPrice: number,
  isLong: boolean = true
): FinancialMetrics => {
  const isCall = option.option_type === 'call';

  if (isLong) {
    return isCall
      ? calculateLongCallMetrics(option, stockPrice)
      : calculateLongPutMetrics(option, stockPrice);
  } else {
    return isCall
      ? calculateShortCallMetrics(option, stockPrice)
      : calculateShortPutMetrics(option, stockPrice);
  }
};

/**
 * Calculate approximate metrics from grid cell data
 * Used when clicking a cell in the options grid
 *
 * @param strike - Strike price
 * @param expiration - Expiration date
 * @param callBid - Call option bid price
 * @param callAsk - Call option ask price
 * @param putBid - Put option bid price
 * @param putAsk - Put option ask price
 * @param stockPrice - Current stock price
 * @param preferredStrategy - Preferred strategy type (default: short put)
 * @returns Financial metrics for the estimated position
 */
export const calculateMetricsFromCellData = (
  strike: number,
  expiration: string,
  callBid?: number,
  callAsk?: number,
  putBid?: number,
  putAsk?: number,
  stockPrice?: number,
  preferredStrategy: 'short_put' | 'short_call' | 'long_call' | 'long_put' = 'short_put'
): FinancialMetrics => {
  const stock = stockPrice || strike; // Fallback to strike if no stock price

  // Determine which option to use based on strategy and available data
  let premium = 0;
  let isCall = false;
  let isLong = false;

  switch (preferredStrategy) {
    case 'short_put':
      premium = putBid || 0;
      isCall = false;
      isLong = false;
      break;
    case 'short_call':
      premium = callBid || 0;
      isCall = true;
      isLong = false;
      break;
    case 'long_call':
      premium = callAsk || 0;
      isCall = true;
      isLong = true;
      break;
    case 'long_put':
      premium = putAsk || 0;
      isCall = false;
      isLong = true;
      break;
  }

  // Calculate based on strategy
  if (isLong) {
    const debit = premium * 100;

    if (isCall) {
      // Long Call
      return {
        netCredit: -debit,
        maxProfit: null, // Unlimited
        maxLoss: -debit,
        breakeven: strike + premium,
        collateral: debit,
        returnOnCapital: null,
        riskRewardRatio: null,
      };
    } else {
      // Long Put
      const maxProfit = (strike * 100) - debit;
      return {
        netCredit: -debit,
        maxProfit: maxProfit,
        maxLoss: -debit,
        breakeven: strike - premium,
        collateral: debit,
        returnOnCapital: (maxProfit / debit) * 100,
        riskRewardRatio: debit / maxProfit,
      };
    }
  } else {
    const credit = premium * 100;

    if (isCall) {
      // Short Call (naked)
      const marginRequirement = (stock * 100 * 0.20) + credit;
      return {
        netCredit: credit,
        maxProfit: credit,
        maxLoss: null, // Unlimited
        breakeven: strike + premium,
        collateral: marginRequirement,
        returnOnCapital: (credit / marginRequirement) * 100,
        riskRewardRatio: null,
      };
    } else {
      // Short Put (cash-secured)
      const collateral = strike * 100;
      const maxLoss = collateral - credit;
      return {
        netCredit: credit,
        maxProfit: credit,
        maxLoss: -maxLoss,
        breakeven: strike - premium,
        collateral: collateral,
        returnOnCapital: (credit / collateral) * 100,
        riskRewardRatio: maxLoss / credit,
      };
    }
  }
};

/**
 * Parameters for simplified metrics calculation
 */
export interface MetricsCalculationParams {
  strategyType: 'short_put' | 'short_call' | 'long_call' | 'long_put';
  strike: number;
  premium: number;
  quantity: number;
  currentStockPrice: number;
}

/**
 * Extended financial metrics with strike and quantity
 */
export interface ExtendedFinancialMetrics extends FinancialMetrics {
  strike: number;
  netDebit?: number; // For long positions (negative netCredit)
}

/**
 * Calculate metrics for options strategies with simplified parameters
 * This is a convenience wrapper for testing and simple calculations
 *
 * @param params - Calculation parameters
 * @returns Extended financial metrics including strike price
 * @throws Error if invalid strategy type, negative strike, or negative premium
 */
export const calculateMetrics = (
  params: MetricsCalculationParams
): ExtendedFinancialMetrics => {
  const { strategyType, strike, premium, quantity, currentStockPrice } = params;

  // Input validation
  if (!['short_put', 'short_call', 'long_call', 'long_put'].includes(strategyType)) {
    throw new Error(`Invalid strategy type: ${strategyType}`);
  }

  if (strike < 0) {
    throw new Error('Strike price cannot be negative');
  }

  if (premium < 0) {
    throw new Error('Premium cannot be negative');
  }

  // Create mock option contract
  const mockOption: OptionContract = {
    ticker: `MOCK_${strategyType}_${strike}`,
    strike: strike,
    option_type: strategyType.includes('call') ? 'call' : 'put',
    expiration_date: new Date().toISOString(),
    last_price: premium,
    bid: strategyType.startsWith('short') ? premium : premium * 0.98,
    ask: strategyType.startsWith('long') ? premium : premium * 1.02,
    volume: 0,
    open_interest: 0,
    implied_volatility: 0,
    delta: 0,
    gamma: 0,
    theta: 0,
    vega: 0,
  };

  // Calculate base metrics
  let baseMetrics: FinancialMetrics;

  switch (strategyType) {
    case 'short_put':
      baseMetrics = calculateShortPutMetrics(mockOption, currentStockPrice);
      break;
    case 'short_call':
      baseMetrics = calculateShortCallMetrics(mockOption, currentStockPrice);
      break;
    case 'long_call':
      baseMetrics = calculateLongCallMetrics(mockOption, currentStockPrice);
      break;
    case 'long_put':
      baseMetrics = calculateLongPutMetrics(mockOption, currentStockPrice);
      break;
    default:
      throw new Error(`Unsupported strategy type: ${strategyType}`);
  }

  // Apply quantity multiplier to dollar amounts
  const multipliedMetrics: FinancialMetrics = {
    netCredit: baseMetrics.netCredit !== null ? baseMetrics.netCredit * quantity : null,
    maxProfit: baseMetrics.maxProfit !== null ? baseMetrics.maxProfit * quantity : null,
    maxLoss: baseMetrics.maxLoss !== null ? baseMetrics.maxLoss * quantity : null,
    breakeven: baseMetrics.breakeven,
    collateral: baseMetrics.collateral !== null ? baseMetrics.collateral * quantity : null,
    returnOnCapital: baseMetrics.returnOnCapital,
    riskRewardRatio: baseMetrics.riskRewardRatio,
  };

  // For long positions, add netDebit (positive version of netCredit)
  const result: ExtendedFinancialMetrics = {
    ...multipliedMetrics,
    strike: strike,
  };

  if (strategyType.startsWith('long') && multipliedMetrics.netCredit !== null) {
    result.netDebit = Math.abs(multipliedMetrics.netCredit);
  }

  return result;
};

/**
 * Format strategy name for display
 *
 * @param strategyType - Strategy type enum
 * @returns Formatted strategy name
 */
export const getStrategyDisplayName = (strategyType: StrategyType): string => {
  const names: Record<StrategyType, string> = {
    [StrategyType.LONG_CALL]: 'Long Call',
    [StrategyType.LONG_PUT]: 'Long Put',
    [StrategyType.SHORT_CALL]: 'Short Call',
    [StrategyType.SHORT_PUT]: 'Short Put',
    [StrategyType.BULL_CALL_SPREAD]: 'Bull Call Spread',
    [StrategyType.BEAR_PUT_SPREAD]: 'Bear Put Spread',
    [StrategyType.IRON_CONDOR]: 'Iron Condor',
  };

  return names[strategyType] || 'Unknown Strategy';
};
