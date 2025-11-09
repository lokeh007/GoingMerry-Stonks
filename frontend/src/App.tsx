/**
 * Main Application Component
 *
 * Root component with React Router for navigation between pages
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import StockScreenerPage from './pages/StockScreenerPage';
import OptionsPage from './pages/OptionsPage';
import TechnicalAnalysisPage from './pages/TechnicalAnalysisPage';
import { apiClient } from './config/api';
import './App.css';

const App: React.FC = () => {
  const [vixValue, setVixValue] = useState<number | null>(null);

  /**
   * Fetch VIX (Volatility Index) data from API
   */
  const fetchVIX = async () => {
    try {
      const response = await apiClient.get<{ value: number; timestamp: string }>(
        '/options/market/vix'
      );
      setVixValue(response.data.value);
    } catch (err) {
      console.error('Error fetching VIX:', err);
    }
  };

  /**
   * Get VIX background color based on value
   */
  const getVixColor = (vix: number): string => {
    if (vix < 18) {
      return '#10b981'; // Green - low volatility
    } else if (vix <= 20) {
      return '#f59e0b'; // Light orange - moderate volatility
    } else {
      return '#ef4444'; // Light red - high volatility
    }
  };

  useEffect(() => {
    fetchVIX();
  }, []);

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <div>
            <h1 className="app-title">GoingMerry-Stonks</h1>
            <p className="app-subtitle">Stock & Options Analysis Platform</p>
          </div>
          {vixValue !== null && (
            <div
              className="vix-indicator"
              style={{ backgroundColor: getVixColor(vixValue) }}
            >
              VIX={vixValue.toFixed(2)}
            </div>
          )}
        </header>

        <Navigation />

        <Routes>
          <Route path="/" element={<Navigate to="/screener" replace />} />
          <Route path="/screener" element={<StockScreenerPage />} />
          <Route path="/options" element={<OptionsPage />} />
          <Route path="/technical" element={<TechnicalAnalysisPage />} />
        </Routes>

        <footer className="app-footer">
          <p>&copy; 2025 GoingMerry-Stonks. Market data provided by Polygon.io & yfinance.</p>
        </footer>
      </div>
    </Router>
  );
};

export default App;
