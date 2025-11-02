/**
 * MetricsExample Component
 *
 * Demonstrates usage of the MetricsDisplay component with sample data
 * for various options strategies.
 */

import React, { useState } from 'react';
import MetricsDisplay from './MetricsDisplay';
import './MetricsExample.css';

/**
 * Sample strategy data
 */
const sampleStrategies = {
  ironCondor: {
    name: 'Iron Condor',
    description: 'Short OTM call spread + short OTM put spread',
    metrics: {
      netCredit: 250,
      maxProfit: 250,
      maxLoss: -750,
      breakeven: [148.5, 151.5],
      collateral: 1000,
    },
  },
  bullPutSpread: {
    name: 'Bull Put Spread',
    description: 'Short put + long put at lower strike',
    metrics: {
      netCredit: 150,
      maxProfit: 150,
      maxLoss: -350,
      breakeven: 148.5,
      collateral: 500,
    },
  },
  longCall: {
    name: 'Long Call',
    description: 'Bullish directional play',
    metrics: {
      netCredit: -525,
      maxProfit: null, // Unlimited
      maxLoss: -525,
      breakeven: 155.25,
      collateral: 525,
    },
  },
  coveredCall: {
    name: 'Covered Call',
    description: '100 shares + short call',
    metrics: {
      netCredit: 450,
      maxProfit: 950,
      maxLoss: -14550, // Stock cost minus premium
      breakeven: 149.55,
      collateral: 15000,
    },
  },
};

type StrategyKey = keyof typeof sampleStrategies;

/**
 * MetricsExample Component
 *
 * Interactive example showing different options strategies and their metrics.
 */
const MetricsExample: React.FC = () => {
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyKey>('ironCondor');

  const strategy = sampleStrategies[selectedStrategy];

  return (
    <div className="metrics-example">
      <div className="example-header">
        <h2 className="example-title">Options Strategy Metrics</h2>
        <p className="example-subtitle">
          Select a strategy to view its financial metrics
        </p>
      </div>

      {/* Strategy Selector */}
      <div className="strategy-selector">
        {(Object.keys(sampleStrategies) as StrategyKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setSelectedStrategy(key)}
            className={`strategy-button ${
              selectedStrategy === key ? 'active' : ''
            }`}
          >
            <div className="strategy-name">{sampleStrategies[key].name}</div>
            <div className="strategy-desc">
              {sampleStrategies[key].description}
            </div>
          </button>
        ))}
      </div>

      {/* Metrics Display */}
      <div className="metrics-container">
        <MetricsDisplay
          title={`${strategy.name} Metrics`}
          netCredit={strategy.metrics.netCredit}
          maxProfit={strategy.metrics.maxProfit}
          maxLoss={strategy.metrics.maxLoss}
          breakeven={strategy.metrics.breakeven}
          collateral={strategy.metrics.collateral}
          format={{
            showPercentages: true,
            currencyDecimals: 2,
            percentageDecimals: 2,
          }}
        />
      </div>

      {/* Additional Info */}
      <div className="example-info">
        <h3 className="info-title">Understanding the Metrics</h3>
        <div className="info-grid">
          <div className="info-card">
            <div className="info-icon">💰</div>
            <h4>Net Credit/Debit</h4>
            <p>
              The initial cash flow. Positive = credit received, Negative =
              debit paid.
            </p>
          </div>
          <div className="info-card">
            <div className="info-icon">📈</div>
            <h4>Max Profit</h4>
            <p>
              The maximum profit potential if the position moves in your favor.
            </p>
          </div>
          <div className="info-card">
            <div className="info-icon">📉</div>
            <h4>Max Loss</h4>
            <p>
              The worst-case scenario if the position moves against you.
            </p>
          </div>
          <div className="info-card">
            <div className="info-icon">⚖️</div>
            <h4>Breakeven</h4>
            <p>
              The stock price(s) at which the position neither profits nor
              loses.
            </p>
          </div>
          <div className="info-card">
            <div className="info-icon">🔒</div>
            <h4>Collateral</h4>
            <p>
              The margin requirement or capital needed to hold the position.
            </p>
          </div>
          <div className="info-card">
            <div className="info-icon">⚡</div>
            <h4>Risk/Reward</h4>
            <p>
              The ratio of maximum loss to maximum profit (lower is better).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsExample;
