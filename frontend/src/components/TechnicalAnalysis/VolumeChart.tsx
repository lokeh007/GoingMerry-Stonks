/**
 * Volume Chart Component
 *
 * Displays trading volume with green (up days) and red (down days) bars
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  Title,
  Tooltip,
  Legend
);

interface VolumeChartProps {
  dates: string[];
  volume: number[];
  open: number[];
  close: number[];
  ticker: string;
}

export const VolumeChart: React.FC<VolumeChartProps> = ({
  dates,
  volume,
  open,
  close,
  ticker
}) => {
  // Color bars green if close > open (up day), red if close < open (down day)
  const barColors = volume.map((_, index) => {
    const isUpDay = close[index] >= open[index];
    return isUpDay
      ? 'rgba(16, 185, 129, 0.7)'  // Green for up days
      : 'rgba(239, 68, 68, 0.7)';   // Red for down days
  });

  const data = {
    labels: dates,
    datasets: [
      {
        label: 'Volume',
        data: volume,
        backgroundColor: barColors,
        borderWidth: 0,
      },
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
        display: false,
      },
      title: {
        display: true,
        text: `${ticker} Volume`,
        color: '#f8fafc',
        font: {
          size: 14,
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
        displayColors: false,
        callbacks: {
          label: function(context: any) {
            const volume = context.parsed.y;
            // Format large numbers (e.g., 50,234,123 → 50.23M)
            if (volume >= 1000000000) {
              return 'Volume: ' + (volume / 1000000000).toFixed(2) + 'B';
            } else if (volume >= 1000000) {
              return 'Volume: ' + (volume / 1000000).toFixed(2) + 'M';
            } else if (volume >= 1000) {
              return 'Volume: ' + (volume / 1000).toFixed(2) + 'K';
            }
            return 'Volume: ' + volume.toLocaleString();
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
            // Format Y-axis labels (e.g., 50000000 → 50M)
            if (value >= 1000000000) {
              return (value / 1000000000).toFixed(1) + 'B';
            } else if (value >= 1000000) {
              return (value / 1000000).toFixed(0) + 'M';
            } else if (value >= 1000) {
              return (value / 1000).toFixed(0) + 'K';
            }
            return value;
          },
        },
      },
    },
  };

  return (
    <div className="chart-container volume-chart">
      <Bar data={data} options={options} />
    </div>
  );
};
