/**
 * Stock Screener Page
 *
 * Main page component for the stock screener with Lynch fundamental filters
 * and results grid. This is the default landing page for the application.
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import LynchFilters from '../components/screener/LynchFilters';
import ScreenerResults from '../components/screener/ScreenerResults';
import {
  AdvancedScreenerRequest,
  ScreenerResponse,
  LynchCategory,
  MarketRegime,
  DEFAULT_FUNDAMENTAL_FILTERS,
  DEFAULT_TECHNICAL_FILTERS,
} from '../types/screener';
import { runAdvancedScreener, parseScreenerURLParams, buildScreenerURLParams } from '../utils/screenerApi';
import './StockScreenerPage.css';

// Category descriptions for each Lynch category
const CATEGORY_DESCRIPTIONS: Record<LynchCategory, string> = {
  [LynchCategory.FAST_GROWERS]:
    "🚀 Fast Growers are small, aggressive companies growing at 20-25% annually. Lynch's most profitable category with potential for 'tenbaggers' but requires careful monitoring of growth sustainability.",
  [LynchCategory.STALWARTS]:
    "🏢 Stalwarts are large, established companies (Coca-Cola, P&G) growing 10-12% annually. Solid defensive holdings that provide steady 30-50% returns over years with low risk.",
  [LynchCategory.SLOW_GROWERS]:
    "🐌 Slow Growers are large, mature companies with single-digit growth. Typically offer dividends but limited price appreciation. Lynch avoided these unless deeply undervalued.",
  [LynchCategory.CYCLICALS]:
    "🔄 Cyclicals are companies whose fortunes rise and fall with economic cycles (autos, airlines, steel). Profitable when bought at the bottom of the cycle and sold at the top.",
  [LynchCategory.TURNAROUNDS]:
    "📈 Turnarounds are companies recovering from setbacks with improving fundamentals. Can produce impressive gains when the turnaround succeeds, but carry bankruptcy risk if it fails.",
  [LynchCategory.ASSET_PLAYS]:
    "💎 Asset Plays are companies with valuable hidden assets (real estate, patents, resources) not reflected in stock price. Success depends on assets being unlocked or recognized by market.",
};

const StockScreenerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // State management
  const [request, setRequest] = useState<AdvancedScreenerRequest>({
    lynch_category: LynchCategory.FAST_GROWERS,
    fundamental_filters: DEFAULT_FUNDAMENTAL_FILTERS,
    technical_filters: DEFAULT_TECHNICAL_FILTERS,
    market_regime: MarketRegime.ANY,
    universe: 'popular',
    page: 1,
    page_size: 50,
  });

  const [response, setResponse] = useState<ScreenerResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Parse URL parameters on mount
  useEffect(() => {
    const params = parseScreenerURLParams(searchParams);
    if (params.lynch_category) {
      setRequest(prev => ({ ...prev, ...params }));
    }
  }, [searchParams]);

  /**
   * Handle "RUN SCREEN" button click
   */
  const handleRunScreen = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await runAdvancedScreener(request);
      setResponse(result);

      // Update URL with current filters for sharing
      const urlParams = buildScreenerURLParams(request);
      setSearchParams(urlParams);
    } catch (err: any) {
      console.error('Screening error:', err);
      setError(err.response?.data?.detail || 'Failed to run screener. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle filter changes from LynchFilters component
   */
  const handleFilterChange = (updatedRequest: Partial<AdvancedScreenerRequest>) => {
    setRequest(prev => ({ ...prev, ...updatedRequest }));
  };

  /**
   * Handle reset filters button
   */
  const handleResetFilters = () => {
    setRequest({
      lynch_category: LynchCategory.FAST_GROWERS,
      fundamental_filters: DEFAULT_FUNDAMENTAL_FILTERS,
      technical_filters: DEFAULT_TECHNICAL_FILTERS,
      market_regime: MarketRegime.ANY,
      universe: 'popular',
      page: 1,
      page_size: 50,
    });
    setResponse(null);
    setSearchParams('');
  };

  /**
   * Handle pagination
   */
  const handlePageChange = (newPage: number) => {
    setRequest(prev => ({ ...prev, page: newPage }));
    // Auto-run when page changes
    setTimeout(() => handleRunScreen(), 100);
  };

  return (
    <div className="stock-screener-page">
      {/* Page Header */}
      <div className="screener-header">
        <div>
          <h1 className="screener-title">Stock Screener</h1>
          <p className="screener-subtitle">
            Find high-potential stocks using Peter Lynch fundamentals
          </p>
        </div>
      </div>

      {/* Section 1: Lynch Fundamental Filters */}
      <div className="screener-section">
        <LynchFilters
          request={request}
          onFilterChange={handleFilterChange}
          onRunScreen={handleRunScreen}
          onReset={handleResetFilters}
          loading={loading}
        />

        {/* Category Description */}
        <div className="category-description">
          {CATEGORY_DESCRIPTIONS[request.lynch_category]}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="screener-actions">
        <button
          className="run-screen-button"
          onClick={handleRunScreen}
          disabled={loading}
        >
          {loading ? 'RUNNING SCREEN...' : '🚀 RUN SCREEN'}
        </button>
        <button
          className="reset-button"
          onClick={handleResetFilters}
          disabled={loading}
        >
          Reset Filters
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="screener-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Section 4: Results Grid */}
      {(response || loading) && (
        <div className="screener-section">
          <ScreenerResults
            response={response}
            loading={loading}
            currentPage={request.page || 1}
            pageSize={request.page_size || 50}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Empty State */}
      {!response && !loading && !error && (
        <div className="empty-state">
          <p>👆 Configure your filters above and click "RUN SCREEN" to find stocks</p>
        </div>
      )}
    </div>
  );
};

export default StockScreenerPage;
