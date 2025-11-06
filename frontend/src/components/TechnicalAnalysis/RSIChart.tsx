/**
 * RSI Chart Component
 *
 * Displays Relative Strength Index with overbought/oversold zones
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

interface RSIChartProps {
  dates: string[];
  rsi: number[];
  currentRSI?: number;
}

export const RSIChart: React.FC<RSIChartProps> = ({
  dates,
  rsi,
  currentRSI
}) => {
  // Create arrays for overbought/oversold zones
  const overboughtLine = new Array(dates.length).fill(70);
  const oversoldLine = new Array(dates.length).fill(30);

  const data = {
    labels: dates,
    datasets: [
      {
        label: 'RSI',
        data: rsi,
        borderColor: '#14b8a6',
        backgroundColor: 'rgba(20, 184, 166, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
        fill: false,
      },
      {
        label: 'Overbought (70)',
        data: overboughtLine,
        borderColor: '#ef4444',
        backgroundColor: 'transparent',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [5, 5],
        fill: false,
      },
      {
        label: 'Oversold (30)',
        data: oversoldLine,
        borderColor: '#10b981',
        backgroundColor: 'transparent',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [5, 5],
        fill: false,
      },
    ],
  };

  const getStatusText = () => {
    if (!currentRSI) return '';
    if (currentRSI > 70) return '🔴 Overbought';
    if (currentRSI < 30) return '🟢 Oversold';
    return '⚪ Neutral';
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
        text: `RSI (Relative Strength Index) ${currentRSI ? '- Current: ' + currentRSI.toFixed(2) + ' ' + getStatusText() : ''}`,
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
              label += context.parsed.y.toFixed(2);
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
        min: 0,
        max: 100,
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
      <Line data={data} options={options} />
    </div>
  );
};
