/**
 * ProfitLossChart Component
 *
 * Displays a profit/loss diagram for options strategies using Chart.js.
 * Shows the characteristic "hockey stick" P/L graph at expiration.
 */

import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
  StrategyParams,
  generatePLData,
  findBreakevens,
  getStrategyDisplayName,
  formatPLCurrency,
} from '../utils/profitLossCalculator';
import '../styles/ProfitLossChart.css';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

/**
 * Props for ProfitLossChart component
 */
interface ProfitLossChartProps {
  /**
   * Strategy parameters for P/L calculation
   */
  strategyParams: StrategyParams;

  /**
   * Chart height in pixels (default: 400)
   */
  height?: number;

  /**
   * Chart width (default: '100%')
   */
  width?: string | number;

  /**
   * Number of data points (default: 100)
   */
  numPoints?: number;

  /**
   * Price range multiplier (default: 0.3 = ±30%)
   */
  priceRange?: number;

  /**
   * Show grid lines (default: true)
   */
  showGrid?: boolean;

  /**
   * Show breakeven markers (default: true)
   */
  showBreakevens?: boolean;

  /**
   * Custom title (default: auto-generated from strategy)
   */
  title?: string;

  /**
   * Optional className
   */
  className?: string;
}

/**
 * ProfitLossChart Component
 *
 * Renders an interactive P/L chart showing profit/loss at different stock prices
 * at expiration. Displays the characteristic hockey-stick shaped diagram for
 * options strategies.
 *
 * @example
 * ```tsx
 * <ProfitLossChart
 *   strategyParams={{
 *     type: 'short_put',
 *     strike: 150,
 *     premium: 5.25,
 *     currentStockPrice: 155
 *   }}
 * />
 * ```
 */
const ProfitLossChart: React.FC<ProfitLossChartProps> = ({
  strategyParams,
  height = 400,
  width = '100%',
  numPoints = 100,
  priceRange = 0.3,
  showGrid = true,
  showBreakevens = true,
  title,
  className = '',
}) => {
  /**
   * Generate P/L data points
   */
  const plData = useMemo(
    () => generatePLData(strategyParams, numPoints, priceRange),
    [strategyParams, numPoints, priceRange]
  );

  /**
   * Find breakeven points
   */
  const breakevens = useMemo(
    () => findBreakevens(plData),
    [plData]
  );

  /**
   * Extract stock prices and P/L values
   */
  const stockPrices = plData.map(d => d.stockPrice);
  const profitLoss = plData.map(d => d.profitLoss);

  /**
   * Find max profit and max loss for annotations
   */
  const maxProfit = Math.max(...profitLoss);
  const maxLoss = Math.min(...profitLoss);

  /**
   * Chart data configuration
   */
  const chartData = {
    labels: stockPrices.map(price => price.toFixed(2)),
    datasets: [
      {
        label: 'Profit/Loss at Expiration',
        data: profitLoss,
        borderColor: 'rgb(102, 126, 234)',
        backgroundColor: (context: any) => {
          const chart = context.chart;
          const { ctx, chartArea } = chart;

          if (!chartArea) return 'rgba(102, 126, 234, 0.1)';

          // Create gradient
          const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
          gradient.addColorStop(0, 'rgba(244, 67, 54, 0.2)'); // Red at bottom (loss)
          gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0)'); // Transparent at zero
          gradient.addColorStop(1, 'rgba(76, 175, 80, 0.2)'); // Green at top (profit)

          return gradient;
        },
        borderWidth: 3,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: 'rgb(102, 126, 234)',
        pointHoverBorderColor: 'white',
        pointHoverBorderWidth: 2,
      },
    ],
  };

  /**
   * Chart options configuration
   */
  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          font: {
            size: 13,
            weight: 600,
          },
          color: '#333',
        },
      },
      title: {
        display: true,
        text: title || `${getStrategyDisplayName(strategyParams.type)} - P/L at Expiration`,
        font: {
          size: 18,
          weight: 'bold',
        },
        color: '#1a1a1a',
        padding: {
          top: 10,
          bottom: 20,
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgb(102, 126, 234)',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          title: (items) => {
            return `Stock Price: $${items[0].label}`;
          },
          label: (item) => {
            const value = item.parsed.y ?? 0;
            return `P/L: ${formatPLCurrency(value)}`;
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Stock Price at Expiration',
          font: {
            size: 14,
            weight: 600,
          },
          color: '#555',
        },
        grid: {
          display: showGrid,
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          maxTicksLimit: 10,
          font: {
            size: 11,
          },
          color: '#666',
          callback: function(value, index) {
            // Show every nth label to avoid crowding
            if (index % Math.ceil(stockPrices.length / 10) === 0) {
              return '$' + stockPrices[index].toFixed(0);
            }
            return '';
          },
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Profit / Loss ($)',
          font: {
            size: 14,
            weight: 600,
          },
          color: '#555',
        },
        grid: {
          display: showGrid,
          color: (context) => {
            // Make zero line more prominent
            if (context.tick.value === 0) {
              return 'rgba(0, 0, 0, 0.3)';
            }
            return 'rgba(0, 0, 0, 0.05)';
          },
          lineWidth: (context) => {
            if (context.tick.value === 0) {
              return 2;
            }
            return 1;
          },
        },
        ticks: {
          font: {
            size: 11,
          },
          color: '#666',
          callback: function(value) {
            return formatPLCurrency(value as number);
          },
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  };

  return (
    <div className={`profit-loss-chart-container ${className}`}>
      {/* Chart */}
      <div className="chart-wrapper" style={{ height, width }}>
        <Line data={chartData} options={options} />
      </div>

      {/* Info Panel */}
      <div className="chart-info-panel">
        {/* Strategy Info */}
        <div className="info-section">
          <h4 className="info-title">Strategy Details</h4>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Strike:</span>
              <span className="info-value">${strategyParams.strike.toFixed(2)}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Premium:</span>
              <span className="info-value">${Math.abs(strategyParams.premium).toFixed(2)}</span>
            </div>
            {strategyParams.currentStockPrice && (
              <div className="info-item">
                <span className="info-label">Current Price:</span>
                <span className="info-value current-price">
                  ${strategyParams.currentStockPrice.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* P/L Summary */}
        <div className="info-section">
          <h4 className="info-title">P/L Summary</h4>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Max Profit:</span>
              <span className={`info-value ${maxProfit > 0 ? 'profit' : ''}`}>
                {formatPLCurrency(maxProfit)}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Max Loss:</span>
              <span className={`info-value ${maxLoss < 0 ? 'loss' : ''}`}>
                {formatPLCurrency(maxLoss)}
              </span>
            </div>
          </div>
        </div>

        {/* Breakeven Points */}
        {showBreakevens && breakevens.length > 0 && (
          <div className="info-section">
            <h4 className="info-title">Breakeven Point{breakevens.length > 1 ? 's' : ''}</h4>
            <div className="breakeven-list">
              {breakevens.map((be, index) => (
                <div key={index} className="breakeven-item">
                  <span className="breakeven-icon">⚖️</span>
                  <span className="breakeven-value">${be.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chart Legend */}
        <div className="chart-legend">
          <div className="legend-item">
            <div className="legend-color profit-zone"></div>
            <span className="legend-label">Profit Zone</span>
          </div>
          <div className="legend-item">
            <div className="legend-color loss-zone"></div>
            <span className="legend-label">Loss Zone</span>
          </div>
          <div className="legend-item">
            <div className="legend-color zero-line"></div>
            <span className="legend-label">Breakeven</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfitLossChart;
