/**
 * OptionsAnalyzer Component
 *
 * Integrated component that combines OptionsGrid and MetricsDisplay.
 * Allows users to click on option cells to calculate and display
 * financial metrics for various strategies.
 */

import React, { useState, useCallback, useMemo } from 'react';
import OptionsGrid from './OptionsGrid';
import MetricsDisplay from './MetricsDisplay';
import ProfitLossChart from './ProfitLossChart';
import { OptionChainResponse } from '../types/options';
import { FinancialMetrics } from '../types/metrics';
import { calculateMetricsFromCellData } from '../utils/metricsCalculator';
import { transformToGridData } from '../utils/optionsDataTransform';
import { StrategyParams } from '../utils/profitLossCalculator';
import './OptionsAnalyzer.css';

/**
 * Strategy selection type
 */
type StrategySelection = 'short_put' | 'short_call' | 'long_call' | 'long_put';

/**
 * Props for OptionsAnalyzer component
 */
interface OptionsAnalyzerProps {
  /**
   * Option chain data from the backend API
   */
  optionChainData: OptionChainResponse;

  /**
   * Optional default strategy (default: 'short_put')
   */
  defaultStrategy?: StrategySelection;

  /**
   * Optional callback when metrics are calculated
   */
  onMetricsCalculated?: (metrics: FinancialMetrics) => void;

  /**
   * Optional className
   */
  className?: string;
}

/**
 * Selected cell information
 */
interface SelectedCellInfo {
  strike: number;
  expiration: string;
  callBid?: number;
  callAsk?: number;
  putBid?: number;
  putAsk?: number;
}

/**
 * OptionsAnalyzer Component
 *
 * Connects the OptionsGrid and MetricsDisplay components.
 * When a user clicks a cell in the grid, calculates metrics
 * and displays them in the MetricsDisplay component.
 *
 * @example
 * ```tsx
 * <OptionsAnalyzer
 *   optionChainData={chainData}
 *   defaultStrategy="short_put"
 *   onMetricsCalculated={(metrics) => console.log(metrics)}
 * />
 * ```
 */
const OptionsAnalyzer: React.FC<OptionsAnalyzerProps> = ({
  optionChainData,
  defaultStrategy = 'short_put',
  onMetricsCalculated,
  className = '',
}) => {
  const [selectedCell, setSelectedCell] = useState<SelectedCellInfo | null>(null);
  const [currentStrategy, setCurrentStrategy] = useState<StrategySelection>(defaultStrategy);

  // Transform option chain data to grid format
  const gridData = useMemo(
    () => transformToGridData(optionChainData),
    [optionChainData]
  );

  /**
   * Handle cell click from OptionsGrid
   */
  const handleCellClick = useCallback(
    (strike: number, expiration: string) => {
      // Get cell data from the grid
      const cellKey = `${strike}-${expiration}`;
      const cellData = gridData.cells.get(cellKey);

      if (!cellData) {
        console.warn(`No data found for strike ${strike}, expiration ${expiration}`);
        return;
      }

      // Extract pricing data
      const selectedInfo: SelectedCellInfo = {
        strike,
        expiration,
        callBid: cellData.callBid,
        callAsk: cellData.callAsk,
        putBid: cellData.putBid,
        putAsk: cellData.putAsk,
      };

      setSelectedCell(selectedInfo);
    },
    [gridData]
  );

  /**
   * Calculate metrics based on selected cell and strategy
   */
  const calculatedMetrics = useMemo<FinancialMetrics | null>(() => {
    if (!selectedCell) return null;

    const metrics = calculateMetricsFromCellData(
      selectedCell.strike,
      selectedCell.expiration,
      selectedCell.callBid,
      selectedCell.callAsk,
      selectedCell.putBid,
      selectedCell.putAsk,
      gridData.stockPrice,
      currentStrategy
    );

    // Notify parent component if callback provided
    if (onMetricsCalculated) {
      onMetricsCalculated(metrics);
    }

    return metrics;
  }, [selectedCell, currentStrategy, gridData.stockPrice, onMetricsCalculated]);

  /**
   * Get strategy display name
   */
  const getStrategyName = (strategy: StrategySelection): string => {
    const names: Record<StrategySelection, string> = {
      short_put: 'Short Put (Cash-Secured)',
      short_call: 'Short Call (Naked)',
      long_call: 'Long Call',
      long_put: 'Long Put',
    };
    return names[strategy];
  };

  /**
   * Get metrics title with selected cell info
   */
  const metricsTitle = useMemo(() => {
    if (!selectedCell) return 'Select an option to analyze';

    const strategyName = getStrategyName(currentStrategy);
    const expirationDate = new Date(selectedCell.expiration).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

    return `${strategyName} - $${selectedCell.strike} (${expirationDate})`;
  }, [selectedCell, currentStrategy]);

  /**
   * Generate P/L chart parameters
   */
  const chartParams = useMemo<StrategyParams | null>(() => {
    if (!selectedCell) return null;

    // Get premium based on strategy type
    let premium = 0;
    switch (currentStrategy) {
      case 'short_put':
        premium = selectedCell.putBid || 0;
        break;
      case 'short_call':
        premium = selectedCell.callBid || 0;
        break;
      case 'long_call':
        premium = -(selectedCell.callAsk || 0); // Negative for debit
        break;
      case 'long_put':
        premium = -(selectedCell.putAsk || 0); // Negative for debit
        break;
    }

    return {
      type: currentStrategy,
      strike: selectedCell.strike,
      premium: premium,
      currentStockPrice: gridData.stockPrice,
    };
  }, [selectedCell, currentStrategy, gridData.stockPrice]);

  return (
    <div className={`options-analyzer ${className}`}>
      {/* Header Section */}
      <div className="analyzer-header">
        <div className="header-info">
          <h2 className="analyzer-title">{gridData.ticker} Options Analyzer</h2>
          <p className="analyzer-subtitle">
            Click any cell to calculate metrics for that option
          </p>
        </div>

        {/* Strategy Selector */}
        <div className="strategy-selector">
          <label className="selector-label">Strategy:</label>
          <div className="strategy-buttons">
            <button
              className={`strategy-btn ${currentStrategy === 'short_put' ? 'active' : ''}`}
              onClick={() => setCurrentStrategy('short_put')}
              title="Sell a put option (bullish, collect premium)"
            >
              Short Put
            </button>
            <button
              className={`strategy-btn ${currentStrategy === 'long_call' ? 'active' : ''}`}
              onClick={() => setCurrentStrategy('long_call')}
              title="Buy a call option (bullish, unlimited upside)"
            >
              Long Call
            </button>
            <button
              className={`strategy-btn ${currentStrategy === 'long_put' ? 'active' : ''}`}
              onClick={() => setCurrentStrategy('long_put')}
              title="Buy a put option (bearish, limited risk)"
            >
              Long Put
            </button>
            <button
              className={`strategy-btn ${currentStrategy === 'short_call' ? 'active' : ''}`}
              onClick={() => setCurrentStrategy('short_call')}
              title="Sell a call option (bearish/neutral, collect premium)"
            >
              Short Call
            </button>
          </div>
        </div>
      </div>

      {/* Options Grid */}
      <div className="analyzer-grid-section">
        <OptionsGrid
          gridData={optionChainData}
          onCellClick={handleCellClick}
          showStockPrice={true}
        />
      </div>

      {/* Metrics Display */}
      <div className="analyzer-metrics-section">
        {selectedCell && calculatedMetrics ? (
          <MetricsDisplay
            title={metricsTitle}
            netCredit={calculatedMetrics.netCredit}
            maxProfit={calculatedMetrics.maxProfit}
            maxLoss={calculatedMetrics.maxLoss}
            breakeven={calculatedMetrics.breakeven}
            collateral={calculatedMetrics.collateral}
            format={{
              showPercentages: true,
              currencyDecimals: 2,
              percentageDecimals: 2,
            }}
          />
        ) : (
          <div className="empty-metrics">
            <div className="empty-icon">📊</div>
            <h3 className="empty-title">No Option Selected</h3>
            <p className="empty-description">
              Click on any cell in the options grid above to see detailed
              financial metrics for that position.
            </p>
            <div className="empty-hint">
              <p>
                <strong>Tip:</strong> Try selecting different strategies using
                the buttons above to compare various approaches.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* P/L Chart */}
      {selectedCell && chartParams && (
        <div className="analyzer-chart-section">
          <ProfitLossChart
            strategyParams={chartParams}
            height={400}
            numPoints={150}
            priceRange={0.3}
            showGrid={true}
            showBreakevens={true}
          />
        </div>
      )}

      {/* Info Footer */}
      {selectedCell && (
        <div className="analyzer-footer">
          <div className="footer-info">
            <span className="info-item">
              <strong>Selected:</strong> ${selectedCell.strike} strike
            </span>
            <span className="info-item">
              <strong>Expiration:</strong> {selectedCell.expiration}
            </span>
            {selectedCell.callBid && (
              <span className="info-item">
                <strong>Call Bid:</strong> ${selectedCell.callBid.toFixed(2)}
              </span>
            )}
            {selectedCell.putBid && (
              <span className="info-item">
                <strong>Put Bid:</strong> ${selectedCell.putBid.toFixed(2)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default OptionsAnalyzer;
