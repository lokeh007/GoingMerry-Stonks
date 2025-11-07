/**
 * Price Chart Component
 *
 * Displays stock price with EMAs overlay using Chart.js
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

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

interface PriceChartProps {
  dates: string[];
  prices: number[];
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

export const PriceChart: React.FC<PriceChartProps> = ({
  dates,
  prices,
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
  const data = {
    labels: dates,
    datasets: [
      {
        label: 'Price',
        data: prices,
        borderColor: '#14b8a6',
        backgroundColor: 'rgba(20, 184, 166, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
        fill: true,
      },
      ...(ema12 ? [{
        label: 'EMA 12',
        data: ema12,
        borderColor: '#f59e0b',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
      }] : []),
      ...(ema26 ? [{
        label: 'EMA 26',
        data: ema26,
        borderColor: '#a855f7',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
      }] : []),
      ...(ema50 ? [{
        label: 'EMA 50',
        data: ema50,
        borderColor: '#ef4444',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [5, 5],
      }] : []),
      ...(ema200 ? [{
        label: 'EMA 200',
        data: ema200,
        borderColor: '#dc2626',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [10, 10],
      }] : []),
      ...(sma20 ? [{
        label: 'SMA 20',
        data: sma20,
        borderColor: '#06b6d4',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [3, 3],
      }] : []),
      ...(sma50 ? [{
        label: 'SMA 50',
        data: sma50,
        borderColor: '#8b5cf6',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [3, 3],
      }] : []),
      ...(sma200 ? [{
        label: 'SMA 200',
        data: sma200,
        borderColor: '#ec4899',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [8, 8],
      }] : []),
      ...(bollingerBands ? [
        {
          label: 'BB Upper',
          data: bollingerBands.upper,
          borderColor: 'rgba(147, 197, 253, 0.5)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          borderDash: [2, 2],
        },
        {
          label: 'BB Middle',
          data: bollingerBands.middle,
          borderColor: '#93c5fd',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
        },
        {
          label: 'BB Lower',
          data: bollingerBands.lower,
          borderColor: 'rgba(147, 197, 253, 0.5)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          borderDash: [2, 2],
        }
      ] : []),
    ],
  };

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
        },
      },
      title: {
        display: true,
        text: `${ticker} Price Chart`,
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
            let label = context.dataset.label || '';
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
      <Line data={data} options={options} />
    </div>
  );
};
