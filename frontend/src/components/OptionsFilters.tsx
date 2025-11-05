/**
 * Options Filters Component
 *
 * Provides filtering controls for options data:
 * - Expiration date selector
 * - ATM strike range selector
 */

import React from 'react';

interface OptionsFiltersProps {
  /** Available expiration dates from API */
  availableExpirations: string[];

  /** Currently selected expiration date */
  selectedExpiration: string | null;

  /** Callback when expiration date changes */
  onExpirationChange: (expiration: string | null) => void;

  /** Current ATM strike range (number of strikes above/below current price) */
  atmStrikeRange: number | null;

  /** Callback when ATM strike range changes */
  onAtmStrikeRangeChange: (range: number | null) => void;

  /** Callback when "Apply Filters" button is clicked */
  onApplyFilters: () => void;

  /** Current stock price for reference */
  stockPrice: number;

  /** Whether filters are disabled (e.g., during loading) */
  disabled?: boolean;
}

/**
 * OptionsFilters Component
 *
 * Displays filtering controls for options chain data.
 * Allows users to filter by expiration date and strikes around ATM.
 */
export const OptionsFilters: React.FC<OptionsFiltersProps> = ({
  availableExpirations,
  selectedExpiration,
  onExpirationChange,
  atmStrikeRange,
  onAtmStrikeRangeChange,
  onApplyFilters,
  stockPrice,
  disabled = false,
}) => {
  /**
   * Handle expiration date selection
   */
  const handleExpirationChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onExpirationChange(value === '' ? null : value);
  };

  /**
   * Handle ATM strike range change
   */
  const handleAtmRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === '') {
      onAtmStrikeRangeChange(null);
    } else {
      const numValue = parseInt(value, 10);
      if (!isNaN(numValue) && numValue >= 1 && numValue <= 50) {
        onAtmStrikeRangeChange(numValue);
      }
    }
  };

  /**
   * Format date for display (convert YYYY-MM-DD to more readable format)
   */
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString + 'T00:00:00');
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  /**
   * Calculate days to expiration
   */
  const getDaysToExpiration = (dateString: string): number => {
    try {
      const expDate = new Date(dateString + 'T00:00:00');
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const diffTime = expDate.getTime() - today.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays;
    } catch {
      return 0;
    }
  };

  return (
    <div className="filters-section">
      <div className="filters-title">
        <span>🎯</span>
        <span>Filter Options</span>
      </div>

      <div className="filters-grid">
        {/* Expiration Date Selector */}
        <div className="filter-group">
          <label htmlFor="expiration-filter" className="filter-label">
            Expiration Date
          </label>
          <select
            id="expiration-filter"
            className="filter-select"
            value={selectedExpiration || ''}
            onChange={handleExpirationChange}
            disabled={disabled || availableExpirations.length === 0}
          >
            <option value="">All Expirations</option>
            {availableExpirations.map((date) => {
              const dte = getDaysToExpiration(date);
              return (
                <option key={date} value={date}>
                  {formatDate(date)} ({dte} {dte === 1 ? 'day' : 'days'})
                </option>
              );
            })}
          </select>
          {availableExpirations.length === 0 && (
            <span className="filter-hint">No expirations available</span>
          )}
        </div>

        {/* ATM Strike Range Selector */}
        <div className="filter-group">
          <label htmlFor="atm-range-filter" className="filter-label">
            ATM Strike Range
          </label>
          <input
            id="atm-range-filter"
            type="number"
            className="filter-input"
            value={atmStrikeRange || ''}
            onChange={handleAtmRangeChange}
            disabled={disabled}
            placeholder="Show all strikes"
            min="1"
            max="50"
          />
          <span className="filter-hint">
            {atmStrikeRange
              ? `Will show ${atmStrikeRange} strikes above/below $${stockPrice.toFixed(2)}`
              : 'Enter number of strikes to show around current price'}
          </span>
        </div>

        {/* Apply Filters Button */}
        <div className="filter-group filter-button-group">
          <button
            className="filter-apply-button"
            onClick={onApplyFilters}
            disabled={disabled}
          >
            {disabled ? 'Loading...' : 'Apply Filters'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default OptionsFilters;
