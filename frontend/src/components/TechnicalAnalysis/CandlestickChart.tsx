/**
 * Candlestick Chart Component
 *
 * Displays OHLC data as candlesticks with optional EMA overlays
 * Note: Uses custom bar implementation to simulate candlesticks
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  PointElement,
  LineElement,
  LineController,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  PointElement,
  LineElement,
  LineController,
  Title,
  Tooltip,
  Legend
);

interface CandlestickChartProps {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  ema12?: number[];
  ema26?: number[];
  ema50?: number[];
  ema200?: number[];
  sma20?: number[];
  sma50?: number[];
  sma200?: number[];
  bollingerBands?: {
    upper: number[];
    middle: number[];
    lower: number[];
  };
  ticker: string;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  dates,
  open,
  high,
  low,
  close,
  ema12,
  ema26,
  ema50,
  ema200,
  sma20,
  sma50,
  sma200,
  bollingerBands,
  ticker
}) => {
  // Color bars based on up/down day
  const barColors = close.map((c, index) => {
    const isGreen = c >= open[index];
    return isGreen
      ? 'rgba(16, 185, 129, 0.8)'  // Green for up days
      : 'rgba(239, 68, 68, 0.8)';   // Red for down days
  });

  const data = {
    labels: dates,
    datasets: [
      {
        type: 'bar' as const,
        label: 'Price',
        data: close,
        backgroundColor: barColors,
        borderColor: barColors,
        borderWidth: 1,
        barThickness: 8,
        order: 2,
      },
      ...(ema12 ? [{
        type: 'line' as const,
        label: 'EMA 12',
        data: ema12,
        borderColor: '#f59e0b',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
        order: 1,
      }] : []),
      ...(ema26 ? [{
        type: 'line' as const,
        label: 'EMA 26',
        data: ema26,
        borderColor: '#a855f7',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
        order: 1,
      }] : []),
      ...(ema50 ? [{
        type: 'line' as const,
        label: 'EMA 50',
        data: ema50,
        borderColor: '#ef4444',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
        order: 1,
      }] : []),
      ...(ema200 ? [{
        type: 'line' as const,
        label: 'EMA 200',
        data: ema200,
        borderColor: '#dc2626',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [10, 10],
        order: 1,
      }] : []),
      ...(sma20 ? [{
        type: 'line' as const,
        label: 'SMA 20',
        data: sma20,
        borderColor: '#06b6d4',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [3, 3],
        order: 1,
      }] : []),
      ...(sma50 ? [{
        type: 'line' as const,
        label: 'SMA 50',
        data: sma50,
        borderColor: '#8b5cf6',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [3, 3],
        order: 1,
      }] : []),
      ...(sma200 ? [{
        type: 'line' as const,
        label: 'SMA 200',
        data: sma200,
        borderColor: '#ec4899',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [8, 8],
        order: 1,
      }] : []),
      ...(bollingerBands ? [
        {
          type: 'line' as const,
          label: 'BB Upper',
          data: bollingerBands.upper,
          borderColor: 'rgba(147, 197, 253, 0.5)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          borderDash: [2, 2],
          order: 1,
        },
        {
          type: 'line' as const,
          label: 'BB Middle',
          data: bollingerBands.middle,
          borderColor: '#93c5fd',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
          order: 1,
        },
        {
          type: 'line' as const,
          label: 'BB Lower',
          data: bollingerBands.lower,
          borderColor: 'rgba(147, 197, 253, 0.5)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          borderDash: [2, 2],
          order: 1,
        }
      ] : []),
    ],
  };

  // Calculate the price range for proper scaling
  const allPrices = [...close, ...open];
  if (ema12) allPrices.push(...ema12.filter((v): v is number => v !== null && v !== undefined));
  if (ema26) allPrices.push(...ema26.filter((v): v is number => v !== null && v !== undefined));
  if (ema50) allPrices.push(...ema50.filter((v): v is number => v !== null && v !== undefined));
  if (ema200) allPrices.push(...ema200.filter((v): v is number => v !== null && v !== undefined));
  if (sma20) allPrices.push(...sma20.filter((v): v is number => v !== null && v !== undefined));
  if (sma50) allPrices.push(...sma50.filter((v): v is number => v !== null && v !== undefined));
  if (sma200) allPrices.push(...sma200.filter((v): v is number => v !== null && v !== undefined));
  if (bollingerBands) {
    allPrices.push(...bollingerBands.upper.filter((v): v is number => v !== null && v !== undefined));
    allPrices.push(...bollingerBands.lower.filter((v): v is number => v !== null && v !== undefined));
  }
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#f8fafc',
          font: {
            size: 12,
          },
          filter: function(item: any) {
            return item.text !== 'Price';
          },
        },
      },
      title: {
        display: true,
        text: `${ticker} Candlestick Chart`,
        color: '#f8fafc',
        font: {
          size: 18,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 20, 25, 0.9)',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        displayColors: true,
        callbacks: {
          label: function(context: any) {
            const index = context.dataIndex;
            const datasetLabel = context.dataset.label;

            // For price bars, show OHLC
            if (datasetLabel === 'Price') {
              const o = open[index];
              const h = high[index];
              const l = low[index];
              const c = close[index];

              return [
                `Open: $${o.toFixed(2)}`,
                `High: $${h.toFixed(2)}`,
                `Low: $${l.toFixed(2)}`,
                `Close: $${c.toFixed(2)}`,
              ];
            }

            // For EMAs, show value
            let label = datasetLabel || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += '$' + context.parsed.y.toFixed(2);
            }
            return label;
          }
        }
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: '#ffffff',
          maxRotation: 45,
          minRotation: 45,
        },
      },
      y: {
        min: minPrice * 0.98,
        max: maxPrice * 1.02,
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: '#ffffff',
          callback: function(value: any) {
            return '$' + value.toFixed(2);
          },
        },
      },
    },
  };

  return (
    <div className="chart-container">
      <Chart type="bar" data={data} options={options} />
    </div>
  );
};
