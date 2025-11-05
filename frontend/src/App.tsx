/**
 * Main Application Component
 *
 * Demonstrates usage of the OptionsAnalyzer component which integrates
 * OptionsGrid and MetricsDisplay for comprehensive options analysis.
 */

import React, { useState, useEffect } from 'react';
import { OptionsAnalyzer, OptionsFilters } from './components';
import { OptionChainResponse } from './types/options';
import { FinancialMetrics } from './types/metrics';
import { apiClient } from './config/api';
import './App.css';

/**
 * App Component
 *
 * Main application entry point that:
 * 1. Fetches option chain data from the backend API
 * 2. Displays filter controls for expiration and ATM range
 * 3. Displays data using OptionsAnalyzer (Grid + Metrics)
 * 4. Handles loading and error states
 * 5. Tracks calculated metrics
 */
const App: React.FC = () => {
  const [optionData, setOptionData] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState<string>('AAPL');
  const [inputTicker, setInputTicker] = useState<string>('AAPL');

  // Filter states
  const [selectedExpiration, setSelectedExpiration] = useState<string | null>(null);
  const [atmStrikeRange, setAtmStrikeRange] = useState<number | null>(null);

  // const [lastMetrics, setLastMetrics] = useState<FinancialMetrics | null>(null); // Reserved for future use

  /**
   * Fetch option chain data from API
   */
  const fetchOptionChain = async (
    symbol: string,
    expiration?: string | null,
    atmRange?: number | null
  ) => {
    setLoading(true);
    setError(null);

    try {
      // Build query parameters
      const params = new URLSearchParams();
      params.append('limit', '250'); // Get more contracts for filtering

      if (expiration) {
        params.append('expiration_date', expiration);
      }

      if (atmRange) {
        params.append('atm_strikes', atmRange.toString());
      }

      // Call backend API endpoint
      const response = await apiClient.get<OptionChainResponse>(
        `/options/${symbol.toUpperCase()}?${params.toString()}`
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
      setSelectedExpiration(null); // Reset filters on new ticker
      setAtmStrikeRange(null);
      fetchOptionChain(inputTicker.trim());
    }
  };

  /**
   * Handle expiration filter change (don't fetch yet)
   */
  const handleExpirationChange = (expiration: string | null) => {
    setSelectedExpiration(expiration);
  };

  /**
   * Handle ATM strike range filter change (don't fetch yet)
   */
  const handleAtmRangeChange = (range: number | null) => {
    setAtmStrikeRange(range);
  };

  /**
   * Handle "Apply Filters" button click
   */
  const handleApplyFilters = () => {
    fetchOptionChain(ticker, selectedExpiration, atmStrikeRange);
  };

  /**
   * Handle metrics calculation
   */
  const handleMetricsCalculated = (metrics: FinancialMetrics) => {
    // setLastMetrics(metrics); // Reserved for future use
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

        {/* Filter Controls - Show when we have option data */}
        {optionData && !loading && !error && (
          <OptionsFilters
            availableExpirations={optionData.available_expirations || []}
            selectedExpiration={selectedExpiration}
            onExpirationChange={handleExpirationChange}
            atmStrikeRange={atmStrikeRange}
            onAtmStrikeRangeChange={handleAtmRangeChange}
            onApplyFilters={handleApplyFilters}
            stockPrice={optionData.stock_price}
            disabled={loading}
          />
        )}

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
