/**
 * PLChartExample Component
 *
 * Demonstrates standalone usage of the ProfitLossChart component
 * with different options strategies.
 */

import React, { useState } from 'react';
import ProfitLossChart from './ProfitLossChart';
import { StrategyParams } from '../utils/profitLossCalculator';
import './PLChartExample.css';

/**
 * Sample strategies for demonstration
 */
const exampleStrategies: Record<string, StrategyParams> = {
  shortPut: {
    type: 'short_put',
    strike: 150,
    premium: 5.25,
    currentStockPrice: 155,
  },
  longCall: {
    type: 'long_call',
    strike: 150,
    premium: -5.25,
    currentStockPrice: 155,
  },
  longPut: {
    type: 'long_put',
    strike: 150,
    premium: -4.75,
    currentStockPrice: 155,
  },
  shortCall: {
    type: 'short_call',
    strike: 150,
    premium: 4.50,
    currentStockPrice: 145,
  },
};

/**
 * PLChartExample Component
 *
 * Interactive example showing P/L charts for various options strategies.
 */
const PLChartExample: React.FC = () => {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('shortPut');
  const [customParams, setCustomParams] = useState<StrategyParams>(exampleStrategies.shortPut);

  /**
   * Handle strategy selection
   */
  const handleStrategyChange = (strategyKey: string) => {
    setSelectedStrategy(strategyKey);
    setCustomParams(exampleStrategies[strategyKey]);
  };

  /**
   * Handle parameter changes
   */
  const handleParamChange = (field: keyof StrategyParams, value: number) => {
    setCustomParams(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <div className="pl-chart-example">
      <div className="example-header">
        <h1 className="example-title">Profit/Loss Chart Examples</h1>
        <p className="example-subtitle">
          Visualize options P/L at expiration with the characteristic hockey-stick diagram
        </p>
      </div>

      {/* Strategy Selector */}
      <div className="strategy-selector">
        <h3 className="selector-title">Select Strategy</h3>
        <div className="strategy-grid">
          <button
            className={`strategy-card ${selectedStrategy === 'shortPut' ? 'active' : ''}`}
            onClick={() => handleStrategyChange('shortPut')}
          >
            <div className="card-title">Short Put</div>
            <div className="card-desc">Cash-Secured, Bullish</div>
            <div className="card-icon">📉➡️📈</div>
          </button>

          <button
            className={`strategy-card ${selectedStrategy === 'longCall' ? 'active' : ''}`}
            onClick={() => handleStrategyChange('longCall')}
          >
            <div className="card-title">Long Call</div>
            <div className="card-desc">Bullish, Unlimited Upside</div>
            <div className="card-icon">📈</div>
          </button>

          <button
            className={`strategy-card ${selectedStrategy === 'longPut' ? 'active' : ''}`}
            onClick={() => handleStrategyChange('longPut')}
          >
            <div className="card-title">Long Put</div>
            <div className="card-desc">Bearish, Limited Risk</div>
            <div className="card-icon">📉</div>
          </button>

          <button
            className={`strategy-card ${selectedStrategy === 'shortCall' ? 'active' : ''}`}
            onClick={() => handleStrategyChange('shortCall')}
          >
            <div className="card-title">Short Call</div>
            <div className="card-desc">Bearish, Collect Premium</div>
            <div className="card-icon">➡️📉</div>
          </button>
        </div>
      </div>

      {/* Parameter Controls */}
      <div className="parameter-controls">
        <h3 className="controls-title">Adjust Parameters</h3>
        <div className="controls-grid">
          <div className="control-group">
            <label className="control-label">
              Strike Price: ${customParams.strike.toFixed(2)}
            </label>
            <input
              type="range"
              min="100"
              max="200"
              step="5"
              value={customParams.strike}
              onChange={(e) => handleParamChange('strike', Number(e.target.value))}
              className="control-slider"
            />
          </div>

          <div className="control-group">
            <label className="control-label">
              Premium: ${Math.abs(customParams.premium).toFixed(2)}
            </label>
            <input
              type="range"
              min="1"
              max="15"
              step="0.25"
              value={Math.abs(customParams.premium)}
              onChange={(e) => {
                const value = Number(e.target.value);
                // Keep sign consistent with strategy type
                const sign = customParams.type.startsWith('short') ? 1 : -1;
                handleParamChange('premium', value * sign);
              }}
              className="control-slider"
            />
          </div>

          <div className="control-group">
            <label className="control-label">
              Current Stock Price: ${customParams.currentStockPrice?.toFixed(2) || 0}
            </label>
            <input
              type="range"
              min="100"
              max="200"
              step="5"
              value={customParams.currentStockPrice || 150}
              onChange={(e) => handleParamChange('currentStockPrice', Number(e.target.value))}
              className="control-slider"
            />
          </div>
        </div>
      </div>

      {/* P/L Chart */}
      <div className="chart-section">
        <ProfitLossChart
          strategyParams={customParams}
          height={450}
          numPoints={150}
          priceRange={0.35}
          showGrid={true}
          showBreakevens={true}
        />
      </div>

      {/* Info Panel */}
      <div className="info-panel">
        <h3 className="info-title">Understanding the Chart</h3>
        <div className="info-grid">
          <div className="info-card">
            <h4>📊 The Hockey Stick</h4>
            <p>
              Options P/L diagrams show a characteristic "hockey stick" shape due to
              asymmetric risk/reward. One direction has limited profit/loss, while the
              other can be unlimited (or limited to strike price).
            </p>
          </div>

          <div className="info-card">
            <h4>⚖️ Breakeven Points</h4>
            <p>
              The point(s) where the P/L line crosses zero. At this stock price at
              expiration, you neither profit nor lose (excluding commissions/fees).
            </p>
          </div>

          <div className="info-card">
            <h4>🎨 Color Zones</h4>
            <p>
              Green shading indicates profit zones (above zero), red shading indicates
              loss zones (below zero). The thick horizontal line represents breakeven.
            </p>
          </div>

          <div className="info-card">
            <h4>💡 Interactive</h4>
            <p>
              Hover over any point on the chart to see the exact P/L at that stock price.
              This helps you understand your position's value at different scenarios.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PLChartExample;
