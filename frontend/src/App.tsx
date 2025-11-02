/**
 * Main Application Component
 *
 * Demonstrates usage of the OptionsAnalyzer component which integrates
 * OptionsGrid and MetricsDisplay for comprehensive options analysis.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { OptionsAnalyzer } from './components';
import { OptionChainResponse } from './types/options';
import { FinancialMetrics } from './types/metrics';
import './App.css';

/**
 * App Component
 *
 * Main application entry point that:
 * 1. Fetches option chain data from the backend API
 * 2. Displays data using OptionsAnalyzer (Grid + Metrics)
 * 3. Handles loading and error states
 * 4. Tracks calculated metrics
 */
const App: React.FC = () => {
  const [optionData, setOptionData] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState<string>('AAPL');
  const [inputTicker, setInputTicker] = useState<string>('AAPL');
  const [lastMetrics, setLastMetrics] = useState<FinancialMetrics | null>(null);

  /**
   * Fetch option chain data from API
   */
  const fetchOptionChain = async (symbol: string) => {
    setLoading(true);
    setError(null);

    try {
      // Call backend API endpoint
      const response = await axios.get<OptionChainResponse>(
        `/options/${symbol.toUpperCase()}?limit=50`
      );

      setOptionData(response.data);
      setTicker(symbol.toUpperCase());
    } catch (err: any) {
      if (err.response) {
        // Server responded with error
        setError(
          err.response.data.detail ||
          `Error ${err.response.status}: Failed to fetch option chain`
        );
      } else if (err.request) {
        // Request made but no response
        setError('Unable to connect to API. Please ensure the backend is running.');
      } else {
        // Other errors
        setError('An unexpected error occurred');
      }
      console.error('Error fetching option chain:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputTicker.trim()) {
      fetchOptionChain(inputTicker.trim());
    }
  };

  /**
   * Handle metrics calculation
   */
  const handleMetricsCalculated = (metrics: FinancialMetrics) => {
    setLastMetrics(metrics);
    console.log('Metrics calculated:', metrics);
  };

  /**
   * Load default data on mount
   */
  useEffect(() => {
    fetchOptionChain('AAPL');
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">GoingMerry-Stonks</h1>
        <p className="app-subtitle">Stock & Options Analysis Platform</p>
      </header>

      <main className="app-main">
        {/* Search Form */}
        <div className="search-section">
          <form onSubmit={handleSubmit} className="search-form">
            <div className="input-group">
              <input
                type="text"
                value={inputTicker}
                onChange={(e) => setInputTicker(e.target.value.toUpperCase())}
                placeholder="Enter ticker symbol (e.g., AAPL)"
                className="ticker-input"
                disabled={loading}
                maxLength={10}
              />
              <button
                type="submit"
                className="search-button"
                disabled={loading || !inputTicker.trim()}
              >
                {loading ? 'Loading...' : 'Get Option Chain'}
              </button>
            </div>
          </form>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="loading-container">
            <div className="spinner"></div>
            <p className="loading-text">Fetching option chain for {inputTicker}...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h3 className="error-title">Error Loading Data</h3>
            <p className="error-message">{error}</p>
            <button onClick={() => fetchOptionChain(ticker)} className="retry-button">
              Retry
            </button>
          </div>
        )}

        {/* Options Analyzer (Grid + Metrics) */}
        {optionData && !loading && !error && (
          <div className="analyzer-container">
            <OptionsAnalyzer
              optionChainData={optionData}
              defaultStrategy="short_put"
              onMetricsCalculated={handleMetricsCalculated}
            />
          </div>
        )}

        {/* Empty State */}
        {!optionData && !loading && !error && (
          <div className="empty-state">
            <p>Enter a ticker symbol to view option chain data</p>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>© 2025 GoingMerry-Stonks | Data provided by Polygon.io</p>
      </footer>
    </div>
  );
};

export default App;
