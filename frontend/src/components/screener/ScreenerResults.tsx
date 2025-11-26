/**
 * Screener Results Component
 *
 * Section 4: Results Grid
 * Displays screening results in an interactive table with pagination and click-through to detail pages
 */

import React from 'react';
import { ScreenerResponse, StockScreenerResult } from '../../types/screener';
import './ScreenerResults.css';

interface ScreenerResultsProps {
  response: ScreenerResponse | null;
  loading: boolean;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

const ScreenerResults: React.FC<ScreenerResultsProps> = ({
  response,
  loading,
  currentPage,
  pageSize,
  onPageChange,
}) => {

  /**
   * Handle ticker click - open Technical Analysis page in new tab
   */
  const handleTickerClick = (ticker: string) => {
    // Open in new tab to keep screener results visible
    window.open(`/technical?ticker=${ticker}`, '_blank', 'noopener,noreferrer');
  };

  /**
   * Format large numbers (market cap, price, etc.)
   */
  const formatNumber = (num: number | undefined, decimals: number = 2): string => {
    if (num === undefined || num === null) return 'N/A';

    if (num >= 1_000_000_000) {
      return `$${(num / 1_000_000_000).toFixed(1)}B`;
    } else if (num >= 1_000_000) {
      return `$${(num / 1_000_000).toFixed(1)}M`;
    } else {
      return `$${num.toFixed(decimals)}`;
    }
  };

  /**
   * Format percentage
   */
  const formatPercent = (num: number | undefined, decimals: number = 1): string => {
    if (num === undefined || num === null) return 'N/A';
    return `${num.toFixed(decimals)}%`;
  };

  /**
   * Get color class for score
   */
  const getScoreClass = (score: number | null | undefined): string => {
    if (score === null || score === undefined) return 'score-poor';
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-fair';
    return 'score-poor';
  };

  // Loading state
  if (loading) {
    return (
      <div className="screener-results">
        <h2 className="section-title">📈 Screening Results</h2>
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Running screener... This may take 3-6 seconds</p>
        </div>
      </div>
    );
  }

  // No results
  if (!response) {
    return null;
  }

  const { total_results, results, screener_name, description } = response;
  const totalPages = Math.ceil(total_results / pageSize);

  return (
    <div className="screener-results">
      {/* Header */}
      <div className="results-header">
        <div>
          <h2 className="section-title">📈 {screener_name}</h2>
          <p className="results-description">{description}</p>
        </div>
        <div className="results-count">
          <strong>{total_results}</strong> stocks found
          {total_results > 0 && (
            <span className="page-info">
              (Page {currentPage} of {totalPages})
            </span>
          )}
        </div>
      </div>

      {/* No Results Message */}
      {total_results === 0 ? (
        <div className="no-results">
          <p>😔 No stocks match your criteria. Try adjusting your filters.</p>
        </div>
      ) : (
        <>
          {/* Results Table */}
          <div className="results-table-container">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Sector</th>
                  <th>Market Cap</th>
                  <th>Price</th>
                  <th>PEG</th>
                  <th>EPS Growth</th>
                  <th>D/E</th>
                  <th>ROE</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {results.map((stock: StockScreenerResult) => (
                  <tr key={stock.ticker} className="result-row">
                    <td>
                      <button
                        className="ticker-button"
                        onClick={() => handleTickerClick(stock.ticker)}
                        title="Click to view technical analysis"
                      >
                        {stock.ticker}
                      </button>
                    </td>
                    <td className="company-cell">{stock.company_name}</td>
                    <td>{stock.sector || 'N/A'}</td>
                    <td>{formatNumber(stock.market_cap, 0)}</td>
                    <td>{formatNumber(stock.price)}</td>
                    <td className={stock.peg_ratio != null && stock.peg_ratio < 1 ? 'value-good' : ''}>
                      {stock.peg_ratio != null ? stock.peg_ratio.toFixed(2) : 'N/A'}
                    </td>
                    <td className={stock.earnings_growth != null && stock.earnings_growth > 15 ? 'value-good' : ''}>
                      {formatPercent(stock.earnings_growth)}
                    </td>
                    <td className={stock.debt_to_equity != null && stock.debt_to_equity < 0.5 ? 'value-good' : ''}>
                      {stock.debt_to_equity != null ? stock.debt_to_equity.toFixed(2) : 'N/A'}
                    </td>
                    <td className={stock.roe != null && stock.roe > 15 ? 'value-good' : ''}>
                      {formatPercent(stock.roe)}
                    </td>
                    <td>
                      <span className={`score-badge ${getScoreClass(stock.score)}`}>
                        {stock.score !== null && stock.score !== undefined ? stock.score.toFixed(0) : 'N/A'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-button"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                ← Previous
              </button>
              <span className="pagination-info">
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="pagination-button"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ScreenerResults;
