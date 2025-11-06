/**
 * Options Analysis Page Component
 *
 * Demonstrates usage of the OptionsAnalyzer component which integrates
 * OptionsGrid and MetricsDisplay for comprehensive options analysis.
 */

import React, { useState, useEffect } from 'react';
import { OptionsAnalyzer, OptionsFilters } from '../components';
import { OptionChainResponse } from '../types/options';
import { FinancialMetrics } from '../types/metrics';
import { apiClient } from '../config/api';

const OptionsPage: React.FC = () => {
  const [optionData, setOptionData] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState<string>('AAPL');
  const [inputTicker, setInputTicker] = useState<string>('AAPL');

  // Filter states
  const [selectedExpiration, setSelectedExpiration] = useState<string | null>(null);
  const [atmStrikeRange, setAtmStrikeRange] = useState<number | null>(null);

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
      const params = new URLSearchParams();
      params.append('limit', '250');

      if (expiration) {
        params.append('expiration_date', expiration);
      }

      if (atmRange) {
        params.append('atm_strikes', atmRange.toString());
      }

      const response = await apiClient.get<OptionChainResponse>(
        `/options/${symbol.toUpperCase()}?${params.toString()}`
      );

      setOptionData(response.data);
      setTicker(symbol.toUpperCase());
    } catch (err: any) {
      if (err.response) {
        setError(
          err.response.data.detail ||
          `Error ${err.response.status}: Failed to fetch option chain`
        );
      } else if (err.request) {
        setError('Unable to connect to API. Please ensure the backend is running.');
      } else {
        setError('An unexpected error occurred');
      }
      console.error('Error fetching option chain:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputTicker.trim()) {
      setSelectedExpiration(null);
      setAtmStrikeRange(null);
      fetchOptionChain(inputTicker.trim());
    }
  };

  const handleExpirationChange = (expiration: string | null) => {
    setSelectedExpiration(expiration);
  };

  const handleAtmRangeChange = (range: number | null) => {
    setAtmStrikeRange(range);
  };

  const handleApplyFilters = () => {
    fetchOptionChain(ticker, selectedExpiration, atmStrikeRange);
  };

  const handleMetricsCalculated = (metrics: FinancialMetrics) => {
    console.log('Metrics calculated:', metrics);
  };

  useEffect(() => {
    fetchOptionChain('AAPL');
  }, []);

  return (
    <div className="options-page">
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

        {/* Filter Controls */}
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
            <p className="loading-text">Loading option chain data...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h3 className="error-title">Error Loading Option Chain</h3>
            <p className="error-message">{error}</p>
            <button onClick={() => fetchOptionChain(ticker)} className="retry-button">
              Retry
            </button>
          </div>
        )}

        {/* Options Grid */}
        {optionData && !loading && !error && (
          <div className="grid-container">
            <OptionsAnalyzer
              optionChainData={optionData}
              onMetricsCalculated={handleMetricsCalculated}
            />
          </div>
        )}

        {/* Empty State */}
        {!optionData && !loading && !error && (
          <div className="empty-state">
            <p>Enter a ticker symbol above to view its option chain</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default OptionsPage;
