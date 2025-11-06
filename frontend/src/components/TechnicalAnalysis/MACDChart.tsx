/**
 * MACD Chart Component
 *
 * Displays MACD line, signal line, and histogram
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend
);

interface MACDChartProps {
  dates: string[];
  macd: {
    macd_line: number[];
    signal_line: number[];
    histogram: number[];
  };
}

export const MACDChart: React.FC<MACDChartProps> = ({
  dates,
  macd
}) => {
  // Color histogram based on positive/negative values
  const histogramColors = macd.histogram.map(value =>
    value >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'
  );

  const data = {
    labels: dates,
    datasets: [
      {
        type: 'bar' as const,
        label: 'Histogram',
        data: macd.histogram,
        backgroundColor: histogramColors,
        borderWidth: 0,
        order: 2,
      },
      {
        type: 'line' as const,
        label: 'MACD Line',
        data: macd.macd_line,
        borderColor: '#14b8a6',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
        order: 1,
      },
      {
        type: 'line' as const,
        label: 'Signal Line',
        data: macd.signal_line,
        borderColor: '#f59e0b',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
        order: 1,
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
        text: 'MACD (Moving Average Convergence Divergence)',
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
              label += context.parsed.y.toFixed(4);
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
          color: '#94a3b8',
          maxRotation: 45,
          minRotation: 45,
        },
      },
      y: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: '#94a3b8',
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
