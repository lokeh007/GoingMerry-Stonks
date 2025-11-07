/**
 * MetricsDisplay Component
 *
 * Displays financial metrics for options positions and strategies in a
 * clean, visually appealing format with proper color coding and formatting.
 */

import React, { useMemo } from 'react';
import { MetricsDisplayFormat } from '../types/metrics';
import '../styles/MetricsDisplay.css';

/**
 * Props for MetricsDisplay component
 */
interface MetricsDisplayProps {
  /**
   * Net credit received (positive) or debit paid (negative)
   */
  netCredit: number | null;

  /**
   * Maximum profit potential
   */
  maxProfit: number | null;

  /**
   * Maximum loss potential
   */
  maxLoss: number | null;

  /**
   * Breakeven price(s) - can be single value or array
   */
  breakeven: number | number[] | null;

  /**
   * Collateral/margin requirement
   */
  collateral: number | null;

  /**
   * Optional display format options
   */
  format?: MetricsDisplayFormat;

  /**
   * Optional title for the metrics section
   */
  title?: string;

  /**
   * Optional className for custom styling
   */
  className?: string;
}

/**
 * MetricsDisplay Component
 *
 * Renders financial metrics in a card-based layout with:
 * - Color-coded values (green for gains, red for losses)
 * - Formatted currency display
 * - Calculated ratios (ROC, risk/reward)
 * - Responsive design
 *
 * @example
 * ```tsx
 * <MetricsDisplay
 *   netCredit={250}
 *   maxProfit={250}
 *   maxLoss={-750}
 *   breakeven={[148.50, 151.50]}
 *   collateral={1000}
 * />
 * ```
 */
const MetricsDisplay: React.FC<MetricsDisplayProps> = ({
  netCredit,
  maxProfit,
  maxLoss,
  breakeven,
  collateral,
  format = {},
  title = 'Position Metrics',
  className = '',
}) => {
  const {
    showPercentages = true,
    currencyDecimals = 2,
    percentageDecimals = 2,
    compact = false,
  } = format;

  /**
   * Format currency value with proper sign and color
   */
  const formatCurrency = (
    value: number | null | undefined,
    showSign: boolean = false
  ): string => {
    if (value === null || value === undefined) {
      return '-';
    }

    const sign = showSign && value > 0 ? '+' : '';
    return `${sign}$${Math.abs(value).toFixed(currencyDecimals)}`;
  };

  /**
   * Format percentage value
   */
  const formatPercentage = (value: number | null | undefined): string => {
    if (value === null || value === undefined) {
      return '';
    }
    return `(${value > 0 ? '+' : ''}${value.toFixed(percentageDecimals)}%)`;
  };

  /**
   * Format breakeven values
   */
  const formatBreakeven = (be: number | number[] | null): string => {
    if (be === null || be === undefined) {
      return '-';
    }

    if (Array.isArray(be)) {
      return be.map(b => `$${b.toFixed(2)}`).join(' / ');
    }

    return `$${be.toFixed(2)}`;
  };

  /**
   * Get CSS class for value (positive/negative coloring)
   */
  const getValueClass = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'value-neutral';
    if (value > 0) return 'value-positive';
    if (value < 0) return 'value-negative';
    return 'value-neutral';
  };

  /**
   * Calculate Return on Capital (ROC)
   */
  const returnOnCapital = useMemo(() => {
    if (
      maxProfit === null ||
      maxProfit === undefined ||
      collateral === null ||
      collateral === undefined ||
      collateral === 0
    ) {
      return null;
    }
    return (maxProfit / collateral) * 100;
  }, [maxProfit, collateral]);

  /**
   * Calculate Risk/Reward Ratio
   */
  const riskRewardRatio = useMemo(() => {
    if (
      maxLoss === null ||
      maxLoss === undefined ||
      maxProfit === null ||
      maxProfit === undefined ||
      maxProfit === 0
    ) {
      return null;
    }
    return Math.abs(maxLoss) / maxProfit;
  }, [maxLoss, maxProfit]);

  /**
   * Determine position type based on net credit/debit
   */
  const positionType = useMemo(() => {
    if (netCredit === null || netCredit === undefined) return null;
    return netCredit >= 0 ? 'Credit' : 'Debit';
  }, [netCredit]);

  return (
    <div className={`metrics-display ${compact ? 'compact' : ''} ${className}`}>
      {/* Header */}
      <div className="metrics-header">
        <h3 className="metrics-title">{title}</h3>
        {positionType && (
          <span className={`position-type ${positionType.toLowerCase()}`}>
            {positionType} Position
          </span>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {/* Net Credit/Debit */}
        <div className="metric-card">
          <div className="metric-label">
            <span className="label-text">Net {positionType || 'Credit/Debit'}</span>
            <span className="label-icon">💰</span>
          </div>
          <div className={`metric-value ${getValueClass(netCredit)}`}>
            {formatCurrency(netCredit, true)}
          </div>
          <div className="metric-description">
            Initial cash flow
          </div>
        </div>

        {/* Max Profit */}
        <div className="metric-card highlight-profit">
          <div className="metric-label">
            <span className="label-text">Max Profit</span>
            <span className="label-icon">📈</span>
          </div>
          <div className={`metric-value ${getValueClass(maxProfit)}`}>
            {formatCurrency(maxProfit, true)}
          </div>
          {showPercentages && collateral && maxProfit && (
            <div className="metric-percentage">
              ROC: {formatPercentage(returnOnCapital)}
            </div>
          )}
          <div className="metric-description">
            Best-case scenario
          </div>
        </div>

        {/* Max Loss */}
        <div className="metric-card highlight-loss">
          <div className="metric-label">
            <span className="label-text">Max Loss</span>
            <span className="label-icon">📉</span>
          </div>
          <div className={`metric-value ${getValueClass(maxLoss)}`}>
            {formatCurrency(maxLoss, true)}
          </div>
          {showPercentages && collateral && maxLoss && (
            <div className="metric-percentage">
              {formatPercentage((maxLoss / collateral) * 100)}
            </div>
          )}
          <div className="metric-description">
            Worst-case scenario
          </div>
        </div>

        {/* Breakeven */}
        <div className="metric-card">
          <div className="metric-label">
            <span className="label-text">Breakeven</span>
            <span className="label-icon">⚖️</span>
          </div>
          <div className="metric-value value-neutral">
            {formatBreakeven(breakeven)}
          </div>
          <div className="metric-description">
            {Array.isArray(breakeven) && breakeven.length > 1
              ? 'Break-even points'
              : 'Break-even point'}
          </div>
        </div>

        {/* Collateral */}
        <div className="metric-card">
          <div className="metric-label">
            <span className="label-text">Collateral</span>
            <span className="label-icon">🔒</span>
          </div>
          <div className="metric-value value-neutral">
            {formatCurrency(collateral)}
          </div>
          <div className="metric-description">
            Margin requirement
          </div>
        </div>

        {/* Risk/Reward Ratio */}
        <div className="metric-card">
          <div className="metric-label">
            <span className="label-text">Risk/Reward</span>
            <span className="label-icon">⚡</span>
          </div>
          <div className="metric-value value-neutral">
            {riskRewardRatio !== null
              ? `${riskRewardRatio.toFixed(2)}:1`
              : '-'}
          </div>
          <div className="metric-description">
            Risk per dollar of reward
          </div>
        </div>
      </div>

      {/* Additional Info Footer */}
      <div className="metrics-footer">
        <div className="info-row">
          <span className="info-label">Return on Capital:</span>
          <span className={`info-value ${getValueClass(returnOnCapital)}`}>
            {returnOnCapital !== null
              ? `${returnOnCapital.toFixed(2)}%`
              : '-'}
          </span>
        </div>
        {maxProfit !== null && maxLoss !== null && (
          <div className="info-row">
            <span className="info-label">Profit Range:</span>
            <span className="info-value">
              {formatCurrency(maxLoss)} to {formatCurrency(maxProfit, true)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricsDisplay;
