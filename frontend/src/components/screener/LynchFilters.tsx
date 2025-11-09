/**
 * Lynch Filters Component
 *
 * Section 1: Lynch Fundamental Filters
 * Interactive filter controls for Peter Lynch screening criteria
 */

import React, { useState, useEffect } from 'react';
import {
  AdvancedScreenerRequest,
  LynchCategory,
  LynchCategoryLabels,
  FundamentalFilters,
} from '../../types/screener';
import { getCategoryPreset } from '../../utils/screenerApi';
import './LynchFilters.css';

interface LynchFiltersProps {
  request: AdvancedScreenerRequest;
  onFilterChange: (updates: Partial<AdvancedScreenerRequest>) => void;
  onRunScreen: () => void;
  onReset: () => void;
  loading: boolean;
}

const LynchFilters: React.FC<LynchFiltersProps> = ({
  request,
  onFilterChange,
  onRunScreen,
  onReset,
  loading,
}) => {
  const [loadingPreset, setLoadingPreset] = useState(false);

  /**
   * Handle Lynch category change and auto-load preset
   */
  const handleCategoryChange = async (category: LynchCategory) => {
    setLoadingPreset(true);
    try {
      const preset = await getCategoryPreset(category);
      onFilterChange({
        lynch_category: category,
        fundamental_filters: preset.filters,
      });
    } catch (err) {
      console.error('Failed to load category preset:', err);
      // Fallback: just change category without preset
      onFilterChange({ lynch_category: category });
    } finally {
      setLoadingPreset(false);
    }
  };

  /**
   * Handle individual filter changes
   */
  const handleFilterUpdate = (key: keyof FundamentalFilters, value: number | undefined) => {
    onFilterChange({
      fundamental_filters: {
        ...request.fundamental_filters,
        [key]: value,
      },
    });
  };

  const filters = request.fundamental_filters || {};

  return (
    <div className="lynch-filters">
      <h2 className="section-title">📊 Lynch Fundamental Filters</h2>
      <p className="section-description">
        Select a category and adjust filters to find stocks matching Peter Lynch's investment criteria
      </p>

      {/* Lynch Category Selector */}
      <div className="filter-group">
        <label className="filter-label">
          <strong>Stock Category:</strong>
        </label>
        <select
          className="category-select"
          value={request.lynch_category}
          onChange={(e) => handleCategoryChange(e.target.value as LynchCategory)}
          disabled={loading || loadingPreset}
        >
          {Object.entries(LynchCategoryLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {loadingPreset && <span className="loading-indicator">Loading preset...</span>}
      </div>

      {/* Filter Grid */}
      <div className="filters-grid">
        {/* PEG Ratio */}
        <div className="filter-item">
          <label className="filter-label">
            Max PEG Ratio
            <span className="filter-hint">Price/Earnings to Growth ratio</span>
          </label>
          <div className="filter-control">
            <input
              type="number"
              className="filter-input"
              value={filters.max_peg_ratio !== undefined ? filters.max_peg_ratio : ''}
              onChange={(e) => handleFilterUpdate('max_peg_ratio', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="0.1"
              min="0"
              max="5"
              placeholder="e.g., 1.0"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.max_peg_ratio !== undefined ? `≤ ${filters.max_peg_ratio}` : 'Any'}
            </span>
          </div>
        </div>

        {/* EPS Growth Range */}
        <div className="filter-item">
          <label className="filter-label">
            EPS Growth Range (%)
            <span className="filter-hint">Earnings per share growth rate</span>
          </label>
          <div className="filter-control-group">
            <input
              type="number"
              className="filter-input filter-input-small"
              value={filters.min_eps_growth !== undefined ? filters.min_eps_growth : ''}
              onChange={(e) => handleFilterUpdate('min_eps_growth', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="1"
              min="0"
              max="100"
              placeholder="Min"
              disabled={loading}
            />
            <span>to</span>
            <input
              type="number"
              className="filter-input filter-input-small"
              value={filters.max_eps_growth !== undefined ? filters.max_eps_growth : ''}
              onChange={(e) => handleFilterUpdate('max_eps_growth', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="1"
              min="0"
              max="100"
              placeholder="Max"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.min_eps_growth !== undefined && filters.max_eps_growth !== undefined
                ? `${filters.min_eps_growth}% - ${filters.max_eps_growth}%`
                : 'Any'}
            </span>
          </div>
        </div>

        {/* Debt-to-Equity */}
        <div className="filter-item">
          <label className="filter-label">
            Max Debt-to-Equity
            <span className="filter-hint">Debt / Equity ratio</span>
          </label>
          <div className="filter-control">
            <input
              type="number"
              className="filter-input"
              value={filters.max_debt_to_equity !== undefined ? filters.max_debt_to_equity : ''}
              onChange={(e) => handleFilterUpdate('max_debt_to_equity', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="0.1"
              min="0"
              max="5"
              placeholder="e.g., 0.6"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.max_debt_to_equity !== undefined ? `≤ ${filters.max_debt_to_equity}` : 'Any'}
            </span>
          </div>
        </div>

        {/* ROE */}
        <div className="filter-item">
          <label className="filter-label">
            Min ROE (%)
            <span className="filter-hint">Return on Equity</span>
          </label>
          <div className="filter-control">
            <input
              type="number"
              className="filter-input"
              value={filters.min_roe !== undefined ? filters.min_roe : ''}
              onChange={(e) => handleFilterUpdate('min_roe', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="1"
              min="0"
              max="100"
              placeholder="e.g., 15"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.min_roe !== undefined ? `≥ ${filters.min_roe}%` : 'Any'}
            </span>
          </div>
        </div>

        {/* Institutional Ownership */}
        <div className="filter-item">
          <label className="filter-label">
            Max Institutional Ownership (%)
            <span className="filter-hint">Percentage held by institutions</span>
          </label>
          <div className="filter-control">
            <input
              type="number"
              className="filter-input"
              value={filters.max_institutional_ownership !== undefined ? filters.max_institutional_ownership : ''}
              onChange={(e) => handleFilterUpdate('max_institutional_ownership', e.target.value ? parseFloat(e.target.value) : undefined)}
              step="1"
              min="0"
              max="100"
              placeholder="e.g., 30"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.max_institutional_ownership !== undefined ? `≤ ${filters.max_institutional_ownership}%` : 'Any'}
            </span>
          </div>
        </div>

        {/* Market Cap */}
        <div className="filter-item">
          <label className="filter-label">
            Min Market Cap ($B)
            <span className="filter-hint">Minimum company size</span>
          </label>
          <div className="filter-control">
            <input
              type="number"
              className="filter-input"
              value={filters.min_market_cap !== undefined ? filters.min_market_cap / 1_000_000_000 : ''}
              onChange={(e) => handleFilterUpdate('min_market_cap', e.target.value ? parseFloat(e.target.value) * 1_000_000_000 : undefined)}
              step="0.1"
              min="0"
              placeholder="e.g., 1.0"
              disabled={loading}
            />
            <span className="filter-value">
              {filters.min_market_cap !== undefined ? `≥ $${(filters.min_market_cap / 1_000_000_000).toFixed(1)}B` : 'Any'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LynchFilters;
