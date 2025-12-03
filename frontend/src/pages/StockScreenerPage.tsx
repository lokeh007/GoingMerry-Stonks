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
import {
  runAdvancedScreener,
  runSmartMoneyScreener,
  parseScreenerURLParams,
  buildScreenerURLParams,
} from '../utils/screenerApi';
import {
  loadCachedScreenerResults,
  formatLastUpdated,
  isCachedResultStale,
} from '../utils/firestoreCache';
import './StockScreenerPage.css';

// Screener type enum
type ScreenerType = 'lynch' | 'smart_money';

// Screener descriptions
const SCREENER_DESCRIPTIONS: Record<ScreenerType, string> = {
  lynch:
    "🏛️ Peter Lynch's fundamental screening strategies for finding high-quality growth stocks at reasonable prices. Categories include Fast Growers, Stalwarts, and more.",
  smart_money:
    "💰 Follow the 'smart money' by tracking unusual options activity. Find stocks where institutions are placing large, aggressive bets before major moves.",
};

// Category descriptions for each Lynch category
const LYNCH_CATEGORY_DESCRIPTIONS: Record<LynchCategory, string> = {
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

  // Screener type state
  const [screenerType, setScreenerType] = useState<ScreenerType>('lynch');

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

  // Smart Money screener params
  const [smartMoneyParams, setSmartMoneyParams] = useState({
    min_call_to_put_ratio: 3.0,
    unusual_volume_multiplier: 2.0,
    universe: 'popular',
  });

  const [response, setResponse] = useState<ScreenerResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Cached results state
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isCached, setIsCached] = useState<boolean>(false);
  const [loadingCached, setLoadingCached] = useState<boolean>(false);

  // Parse URL parameters on mount
  useEffect(() => {
    const params = parseScreenerURLParams(searchParams);
    if (params.lynch_category) {
      setRequest(prev => ({ ...prev, ...params }));
    }
  }, [searchParams]);

  // Load cached results when switching to Smart Money
  useEffect(() => {
    const loadCached = async () => {
      // Only load cached results for screeners that support it
      if (screenerType !== 'smart_money') {
        setIsCached(false);
        setLastUpdated(null);
        return;
      }

      setLoadingCached(true);
      setError(null);

      try {
        console.log(`[StockScreener] Loading cached results for: ${screenerType}`);

        const cached = await loadCachedScreenerResults(screenerType);

        if (cached) {
          setResponse(cached.data);
          setLastUpdated(cached.lastUpdated);
          setIsCached(true);
          console.log(`[StockScreener] Loaded cached results:`, {
            screener: screenerType,
            resultCount: cached.data.results.length,
            lastUpdated: cached.lastUpdated
          });
        } else {
          console.log(`[StockScreener] No cached results found for: ${screenerType}`);
          setResponse(null);
          setIsCached(false);
          setLastUpdated(null);
        }
      } catch (err: any) {
        console.error(`[StockScreener] Error loading cached results:`, err);
        // Don't show error to user - just fall back to real-time screening
        setIsCached(false);
        setLastUpdated(null);
      } finally {
        setLoadingCached(false);
      }
    };

    loadCached();
  }, [screenerType]);

  /**
   * Handle "RUN SCREEN" button click (runs real-time screening, not cached)
   */
  const handleRunScreen = async () => {
    setLoading(true);
    setError(null);
    setIsCached(false);  // Mark as real-time results
    setLastUpdated(null);

    try {
      let result: ScreenerResponse;

      // Call different API based on screener type
      if (screenerType === 'lynch') {
        result = await runAdvancedScreener(request);
        // Update URL with current filters for sharing
        const urlParams = buildScreenerURLParams(request);
        setSearchParams(urlParams);
      } else {
        // smart_money
        result = await runSmartMoneyScreener(smartMoneyParams);
      }

      setResponse(result);
      setLastUpdated(new Date().toISOString());  // Set current time as last updated
    } catch (err: any) {
      console.error('Screening error:', err);
      setError(err.response?.data?.detail || 'Failed to run screener. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle screener type change
   */
  const handleScreenerTypeChange = (type: ScreenerType) => {
    setScreenerType(type);
    setResponse(null); // Clear results when switching screeners
    setError(null);
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
            Find high-potential stocks using multiple screening strategies
          </p>
        </div>
      </div>

      {/* Screener Type Selector */}
      <div className="screener-type-selector">
        <button
          className={`type-tab ${screenerType === 'lynch' ? 'active' : ''}`}
          onClick={() => handleScreenerTypeChange('lynch')}
        >
          🏛️ Lynch Fundamentals
        </button>
        <button
          className={`type-tab ${screenerType === 'smart_money' ? 'active' : ''}`}
          onClick={() => handleScreenerTypeChange('smart_money')}
        >
          💰 Smart Money
        </button>
      </div>

      {/* Screener Description */}
      <div className="screener-description-box">
        {SCREENER_DESCRIPTIONS[screenerType]}
      </div>

      {/* Conditional Filters Based on Screener Type */}
      <div className="screener-section">
        {screenerType === 'lynch' && (
          <>
            <LynchFilters
              request={request}
              onFilterChange={handleFilterChange}
              onRunScreen={handleRunScreen}
              onReset={handleResetFilters}
              loading={loading}
            />
            <div className="category-description">
              {LYNCH_CATEGORY_DESCRIPTIONS[request.lynch_category]}
            </div>
          </>
        )}

        {screenerType === 'smart_money' && (
          <div className="simple-filters">
            <h3>Options Flow Filters</h3>
            <div className="filter-grid">
              <div className="filter-item">
                <label>Min Call/Put Ratio:</label>
                <input
                  type="number"
                  step="0.1"
                  value={smartMoneyParams.min_call_to_put_ratio}
                  onChange={(e) =>
                    setSmartMoneyParams({
                      ...smartMoneyParams,
                      min_call_to_put_ratio: parseFloat(e.target.value),
                    })
                  }
                  disabled={loading}
                />
                <small>Bullish conviction threshold (default: 3.0)</small>
              </div>
              <div className="filter-item">
                <label>Volume Multiplier:</label>
                <input
                  type="number"
                  step="0.1"
                  value={smartMoneyParams.unusual_volume_multiplier}
                  onChange={(e) =>
                    setSmartMoneyParams({
                      ...smartMoneyParams,
                      unusual_volume_multiplier: parseFloat(e.target.value),
                    })
                  }
                  disabled={loading}
                />
                <small>Unusual volume threshold (default: 2.0x average)</small>
              </div>
              <div className="filter-item">
                <label>Stock Universe:</label>
                <select
                  value={smartMoneyParams.universe}
                  onChange={(e) =>
                    setSmartMoneyParams({
                      ...smartMoneyParams,
                      universe: e.target.value,
                    })
                  }
                  disabled={loading}
                >
                  <option value="popular">Popular (46 stocks)</option>
                  <option value="sp500_sample">S&P 500 Sample (41 stocks)</option>
                  <option value="tech">Technology (31 stocks)</option>
                </select>
              </div>
            </div>
          </div>
        )}
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
