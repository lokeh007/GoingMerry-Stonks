/**
 * TypeScript type definitions for financial metrics.
 *
 * These interfaces define the shape of financial metrics data
 * for options trading strategies.
 */

/**
 * Financial metrics for an options position or strategy
 */
export interface FinancialMetrics {
  /**
   * Net credit received (positive) or debit paid (negative)
   * Represents the initial cash flow when entering the position
   */
  netCredit: number | null;

  /**
   * Maximum profit potential
   * For credit strategies, this is typically the net credit
   * For debit strategies, this is the spread width minus debit
   */
  maxProfit: number | null;

  /**
   * Maximum loss potential
   * The worst-case scenario if the position moves against you
   */
  maxLoss: number | null;

  /**
   * Breakeven price(s)
   * The stock price(s) at which the position breaks even
   * Can be a single value or multiple values (array)
   */
  breakeven: number | number[] | null;

  /**
   * Collateral/margin requirement
   * The amount of capital required to maintain the position
   */
  collateral: number | null;

  /**
   * Optional: Return on capital (ROC)
   * Calculated as (maxProfit / collateral) * 100
   */
  returnOnCapital?: number | null;

  /**
   * Optional: Risk/reward ratio
   * Calculated as maxLoss / maxProfit
   */
  riskRewardRatio?: number | null;
}

/**
 * Display format options for metrics
 */
export interface MetricsDisplayFormat {
  /**
   * Show percentage values alongside dollar amounts
   */
  showPercentages?: boolean;

  /**
   * Number of decimal places for currency (default: 2)
   */
  currencyDecimals?: number;

  /**
   * Number of decimal places for percentages (default: 2)
   */
  percentageDecimals?: number;

  /**
   * Compact mode - smaller, condensed display
   */
  compact?: boolean;
}
