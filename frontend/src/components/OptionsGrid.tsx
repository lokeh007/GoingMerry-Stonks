/**
 * OptionsGrid Component
 *
 * Displays option chain data in a grid/table format with strikes as rows
 * and expiration dates as columns. Shows net credit for each cell.
 */

import React, { useMemo } from 'react';
import { OptionChainResponse } from '../types/options';
import { transformToGridData, formatCurrency, formatDate } from '../utils/optionsDataTransform';
import '../styles/OptionsGrid.css';

/**
 * Props for OptionsGrid component
 */
interface OptionsGridProps {
  /**
   * Option chain data from the backend API
   */
  gridData: OptionChainResponse;

  /**
   * Optional callback when a cell is clicked
   */
  onCellClick?: (strike: number, expiration: string) => void;

  /**
   * Optional class name for styling
   */
  className?: string;

  /**
   * Show stock price in header (default: true)
   */
  showStockPrice?: boolean;
}

/**
 * OptionsGrid Component
 *
 * Renders option chain data as an HTML table with:
 * - Rows: Strike prices (sorted ascending)
 * - Columns: Expiration dates (sorted chronologically)
 * - Cells: Net credit values
 *
 * @example
 * ```tsx
 * <OptionsGrid
 *   gridData={optionChainResponse}
 *   onCellClick={(strike, expiration) => console.log(strike, expiration)}
 * />
 * ```
 */
const OptionsGrid: React.FC<OptionsGridProps> = ({
  gridData,
  onCellClick,
  className = '',
  showStockPrice = true,
}) => {
  // Transform data into grid structure
  const grid = useMemo(() => transformToGridData(gridData), [gridData]);

  /**
   * Handle cell click event
   */
  const handleCellClick = (strike: number, expiration: string) => {
    if (onCellClick) {
      onCellClick(strike, expiration);
    }
  };

  /**
   * Get cell key for Map lookup
   */
  const getCellKey = (strike: number, expiration: string): string => {
    return `${strike}-${expiration}`;
  };

  /**
   * Determine if strike is at-the-money (ATM)
   */
  const isATM = (strike: number): boolean => {
    const threshold = grid.stockPrice * 0.02; // Within 2% of stock price
    return Math.abs(strike - grid.stockPrice) <= threshold;
  };

  /**
   * Determine if strike is in-the-money (ITM) for calls
   */
  const isITM = (strike: number): boolean => {
    return strike < grid.stockPrice;
  };

  /**
   * Get CSS class for strike row
   */
  const getStrikeRowClass = (strike: number): string => {
    if (isATM(strike)) return 'strike-atm';
    if (isITM(strike)) return 'strike-itm';
    return 'strike-otm';
  };

  return (
    <div className={`options-grid-container ${className}`}>
      {/* Header Section */}
      <div className="options-grid-header">
        <h2 className="grid-title">
          {grid.ticker} Option Chain
        </h2>
        {showStockPrice && (
          <div className="stock-price">
            Stock Price: <span className="price-value">{formatCurrency(grid.stockPrice)}</span>
          </div>
        )}
        <div className="contract-count">
          Total Contracts: {gridData.total_contracts}
        </div>
      </div>

      {/* Grid Table */}
      <div className="options-grid-wrapper">
        <table className="options-grid-table">
          <thead>
            <tr>
              <th className="header-strike">Strike</th>
              {grid.expirations.map(expiration => (
                <th key={expiration} className="header-expiration">
                  {formatDate(expiration)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.strikes.map(strike => (
              <tr key={strike} className={`strike-row ${getStrikeRowClass(strike)}`}>
                {/* Strike Price Column */}
                <td className="cell-strike">
                  {formatCurrency(strike)}
                  {isATM(strike) && <span className="atm-indicator">ATM</span>}
                </td>

                {/* Data Cells */}
                {grid.expirations.map(expiration => {
                  const cellData = grid.cells.get(getCellKey(strike, expiration));
                  const hasData = cellData && cellData.netCredit !== null;

                  return (
                    <td
                      key={getCellKey(strike, expiration)}
                      className={`cell-data ${hasData ? 'has-data' : 'no-data'} ${
                        onCellClick ? 'clickable' : ''
                      }`}
                      onClick={() => hasData && handleCellClick(strike, expiration)}
                      title={
                        cellData
                          ? `Strike: ${formatCurrency(strike)}\n` +
                            `Expiration: ${formatDate(expiration)}\n` +
                            `Call Bid: ${formatCurrency(cellData.callBid)}\n` +
                            `Put Bid: ${formatCurrency(cellData.putBid)}`
                          : 'No data available'
                      }
                    >
                      {hasData ? (
                        <div className="cell-content">
                          <span className="net-credit">
                            {formatCurrency(cellData.netCredit)}
                          </span>
                          {cellData.call?.implied_volatility !== undefined &&
                           cellData.call.implied_volatility !== null && (
                            <span className="iv-display">
                              IV: {(cellData.call.implied_volatility * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="no-data-indicator">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer/Legend */}
      <div className="options-grid-footer">
        <div className="legend">
          <div className="legend-item">
            <span className="legend-color strike-itm-color"></span>
            <span className="legend-label">ITM (In-the-Money)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color strike-atm-color"></span>
            <span className="legend-label">ATM (At-the-Money)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color strike-otm-color"></span>
            <span className="legend-label">OTM (Out-of-the-Money)</span>
          </div>
        </div>
        <div className="grid-note">
          * Net credit values shown are based on bid prices
        </div>
      </div>
    </div>
  );
};

export default OptionsGrid;
