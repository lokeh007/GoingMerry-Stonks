/**
 * Gann Square of 9 Page
 *
 * Interactive page for calculating and visualizing Gann Square of 9 support/resistance levels.
 * W.D. Gann's mathematical technique for identifying key price levels.
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchGannLevels } from '../utils/gannApi';
import { GannLevelsResponse } from '../types/gann';
import './GannSquarePage.css';

const GannSquarePage: React.FC = () => {
  const [searchParams] = useSearchParams();

  // Get ticker from URL parameter or default to 'AAPL'
  const urlTicker = searchParams.get('ticker')?.toUpperCase() || 'AAPL';

  const [ticker, setTicker] = useState<string>(urlTicker);
  const [inputTicker, setInputTicker] = useState<string>(urlTicker);
  const [numLevels, setNumLevels] = useState<number>(5);
  const [referencePrice, setReferencePrice] = useState<string>('');
  const [gannData, setGannData] = useState<GannLevelsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch Gann levels from API
   */
  const loadGannLevels = async (symbol: string, levels: number, refPrice?: number) => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchGannLevels({
        ticker: symbol,
        num_levels: levels,
        reference_price: refPrice,
      });
      setGannData(data);
      setTicker(symbol.toUpperCase());
    } catch (err: any) {
      console.error('Gann calculation error:', err);
      if (err.response) {
        setError(
          err.response.data.detail ||
          `Error ${err.response.status}: Failed to calculate Gann levels`
        );
      } else if (err.request) {
        setError('Unable to connect to API. Please ensure the backend is running.');
      } else {
        setError('An unexpected error occurred');
      }
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
      const refPrice = referencePrice ? parseFloat(referencePrice) : undefined;
      loadGannLevels(inputTicker.trim(), numLevels, refPrice);
    }
  };

  /**
   * Load data on mount with ticker from URL
   */
  useEffect(() => {
    loadGannLevels(urlTicker, numLevels);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Format price for display
   */
  const formatPrice = (price: number | null | undefined): string => {
    if (price === null || price === undefined) return 'N/A';
    return `$${price.toFixed(2)}`;
  };

  /**
   * Get position description with emoji
   */
  const getPositionDisplay = (position: string): { text: string; emoji: string } => {
    switch (position) {
      case 'at_support':
        return { text: 'At Support Level', emoji: '🟢' };
      case 'at_resistance':
        return { text: 'At Resistance Level', emoji: '🔴' };
      case 'between_levels':
        return { text: 'Between Levels', emoji: '🟡' };
      default:
        return { text: 'Unknown Position', emoji: '⚪' };
    }
  };

  return (
    <div className="gann-page">
      {/* Page Header */}
      <div className="gann-header">
        <h1 className="gann-title">Gann Square of 9</h1>
        <p className="gann-subtitle">
          Calculate W.D. Gann's mathematical support and resistance levels
        </p>
      </div>

      {/* Search Form */}
      <div className="gann-search-section">
        <form onSubmit={handleSubmit} className="gann-search-form">
          <div className="gann-input-row">
            <div className="gann-input-group">
              <label className="gann-label">Ticker Symbol</label>
              <input
                type="text"
                value={inputTicker}
                onChange={(e) => setInputTicker(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL"
                className="gann-ticker-input"
                disabled={loading}
                maxLength={10}
                required
              />
            </div>

            <div className="gann-input-group">
              <label className="gann-label">Number of Levels</label>
              <select
                value={numLevels}
                onChange={(e) => setNumLevels(parseInt(e.target.value))}
                className="gann-level-select"
                disabled={loading}
              >
                {[3, 5, 7, 10].map(num => (
                  <option key={num} value={num}>{num} levels</option>
                ))}
              </select>
            </div>

            <div className="gann-input-group">
              <label className="gann-label">
                Reference Price <span className="optional">(optional)</span>
              </label>
              <input
                type="number"
                value={referencePrice}
                onChange={(e) => setReferencePrice(e.target.value)}
                placeholder="Auto: 52-week low"
                className="gann-price-input"
                disabled={loading}
                step="0.01"
                min="0"
              />
            </div>

            <button
              type="submit"
              className="gann-calculate-button"
              disabled={loading || !inputTicker.trim()}
            >
              {loading ? 'Calculating...' : '📐 Calculate Levels'}
            </button>
          </div>
        </form>
      </div>

      {/* Info Box */}
      <div className="gann-info-box">
        <h3>ℹ️ About Gann Square of 9</h3>
        <p>
          The Gann Square of 9 is a mathematical tool developed by legendary trader W.D. Gann.
          It uses a spiral pattern with key angles (90°, 180°, 270°, 360°) to identify
          important support and resistance price levels. These levels often act as pivot points
          where price action may reverse or consolidate.
        </p>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="gann-loading-container">
          <div className="gann-spinner"></div>
          <p className="gann-loading-text">Calculating Gann levels...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="gann-error-container">
          <div className="gann-error-icon">⚠️</div>
          <h3 className="gann-error-title">Error</h3>
          <p className="gann-error-message">{error}</p>
          <button onClick={() => loadGannLevels(ticker, numLevels)} className="gann-retry-button">
            Retry
          </button>
        </div>
      )}

      {/* Results */}
      {gannData && !loading && !error && (
        <div className="gann-results">
          {/* Summary Cards */}
          <div className="gann-summary-cards">
            <div className="gann-card">
              <div className="card-label">Current Price</div>
              <div className="card-value price-current">
                {formatPrice(gannData.current_price)}
              </div>
            </div>

            <div className="gann-card">
              <div className="card-label">Reference Price</div>
              <div className="card-value">
                {formatPrice(gannData.reference_price)}
              </div>
              <div className="card-hint">
                {gannData.week_52_low ? '52-Week Low' : 'Custom'}
              </div>
            </div>

            <div className="gann-card">
              <div className="card-label">Position</div>
              <div className="card-value">
                {getPositionDisplay(gannData.current_position).emoji}
                {' '}
                {getPositionDisplay(gannData.current_position).text}
              </div>
            </div>

            <div className="gann-card">
              <div className="card-label">Nearest Support</div>
              <div className="card-value price-support">
                {formatPrice(gannData.nearest_support)}
              </div>
              {gannData.nearest_support && (
                <div className="card-hint">
                  {(((gannData.current_price - gannData.nearest_support) / gannData.current_price) * 100).toFixed(2)}% below
                </div>
              )}
            </div>

            <div className="gann-card">
              <div className="card-label">Nearest Resistance</div>
              <div className="card-value price-resistance">
                {formatPrice(gannData.nearest_resistance)}
              </div>
              {gannData.nearest_resistance && (
                <div className="card-hint">
                  {(((gannData.nearest_resistance - gannData.current_price) / gannData.current_price) * 100).toFixed(2)}% above
                </div>
              )}
            </div>
          </div>

          {/* Levels Tables */}
          <div className="gann-levels-container">
            {/* Support Levels */}
            <div className="gann-levels-section">
              <h3 className="levels-title">🟢 Support Levels (Below Current Price)</h3>
              <div className="levels-table">
                {gannData.support_levels.length > 0 ? (
                  gannData.support_levels.map((level, idx) => (
                    <div key={idx} className="level-row support-row">
                      <div className="level-number">S{idx + 1}</div>
                      <div className="level-price">{formatPrice(level)}</div>
                      <div className="level-distance">
                        {(((gannData.current_price - level) / gannData.current_price) * 100).toFixed(2)}% below
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="no-levels">No support levels calculated</div>
                )}
              </div>
            </div>

            {/* Resistance Levels */}
            <div className="gann-levels-section">
              <h3 className="levels-title">🔴 Resistance Levels (Above Current Price)</h3>
              <div className="levels-table">
                {gannData.resistance_levels.length > 0 ? (
                  gannData.resistance_levels.map((level, idx) => (
                    <div key={idx} className="level-row resistance-row">
                      <div className="level-number">R{idx + 1}</div>
                      <div className="level-price">{formatPrice(level)}</div>
                      <div className="level-distance">
                        {(((level - gannData.current_price) / gannData.current_price) * 100).toFixed(2)}% above
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="no-levels">No resistance levels calculated</div>
                )}
              </div>
            </div>
          </div>

          {/* 52-Week Range (if available) */}
          {gannData.week_52_low && gannData.week_52_high && (
            <div className="gann-range-info">
              <h3>📊 52-Week Range</h3>
              <div className="range-bar-container">
                <div className="range-labels">
                  <span className="range-low">Low: {formatPrice(gannData.week_52_low)}</span>
                  <span className="range-high">High: {formatPrice(gannData.week_52_high)}</span>
                </div>
                <div className="range-bar">
                  <div
                    className="range-current"
                    style={{
                      left: `${((gannData.current_price - gannData.week_52_low) / (gannData.week_52_high - gannData.week_52_low)) * 100}%`
                    }}
                  >
                    <div className="range-marker"></div>
                    <div className="range-label">Current</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GannSquarePage;
