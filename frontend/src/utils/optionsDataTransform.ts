/**
 * Utility functions for transforming options data.
 *
 * These functions convert the flat option chain API response into
 * a grid structure suitable for table rendering.
 */

import { OptionChainResponse, OptionContract, GridData, GridCellData } from '../types/options';

/**
 * Calculate net credit for an option position.
 *
 * Net credit represents the premium received when selling an option.
 * Uses the bid price (what you'd receive) as the net credit.
 *
 * @param contract - Option contract data
 * @returns Net credit value or null if unavailable
 */
export const calculateNetCredit = (contract?: OptionContract): number | null => {
  if (!contract) return null;

  // Net credit is the bid price (what you receive when selling)
  if (contract.bid !== undefined && contract.bid !== null) {
    return contract.bid;
  }

  // Fallback to mid-price if bid not available
  if (contract.ask !== undefined && contract.last_price !== undefined) {
    return (contract.ask + contract.last_price) / 2;
  }

  // Fallback to last price
  return contract.last_price ?? null;
};

/**
 * Generate a unique key for a grid cell.
 *
 * @param strike - Strike price
 * @param expiration - Expiration date
 * @returns Unique key string
 */
const getCellKey = (strike: number, expiration: string): string => {
  return `${strike}-${expiration}`;
};

/**
 * Transform option chain API response into grid data structure.
 *
 * Organizes options by strike price (rows) and expiration date (columns)
 * for easy table rendering.
 *
 * @param optionChain - Raw option chain data from API
 * @returns Organized grid data structure
 */
export const transformToGridData = (optionChain: OptionChainResponse): GridData => {
  // Collect unique strikes and expirations
  const strikesSet = new Set<number>();
  const expirationsSet = new Set<string>();

  // Build maps for quick lookup
  const callsMap = new Map<string, OptionContract>();
  const putsMap = new Map<string, OptionContract>();

  // Process calls
  optionChain.calls.forEach(call => {
    strikesSet.add(call.strike);
    expirationsSet.add(call.expiration_date);
    callsMap.set(getCellKey(call.strike, call.expiration_date), call);
  });

  // Process puts
  optionChain.puts.forEach(put => {
    strikesSet.add(put.strike);
    expirationsSet.add(put.expiration_date);
    putsMap.set(getCellKey(put.strike, put.expiration_date), put);
  });

  // Sort strikes (ascending)
  const strikes = Array.from(strikesSet).sort((a, b) => a - b);

  // Sort expirations (chronological)
  const expirations = Array.from(expirationsSet).sort();

  // Build grid cells
  const cells = new Map<string, GridCellData>();

  strikes.forEach(strike => {
    expirations.forEach(expiration => {
      const key = getCellKey(strike, expiration);
      const call = callsMap.get(key);
      const put = putsMap.get(key);

      // Calculate net credit (for now, using call bid as primary)
      // In a real scenario, this might be based on strategy selection
      const netCredit = calculateNetCredit(call) ?? calculateNetCredit(put);

      cells.set(key, {
        strike,
        expiration,
        netCredit,
        callBid: call?.bid,
        callAsk: call?.ask,
        putBid: put?.bid,
        putAsk: put?.ask,
        call,
        put,
      });
    });
  });

  return {
    ticker: optionChain.ticker,
    stockPrice: optionChain.stock_price,
    strikes,
    expirations,
    cells,
  };
};

/**
 * Format currency value for display.
 *
 * @param value - Numeric value
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string
 */
export const formatCurrency = (value: number | null | undefined, decimals: number = 2): string => {
  if (value === null || value === undefined) {
    return '-';
  }
  return `$${value.toFixed(decimals)}`;
};

/**
 * Format date for display.
 *
 * @param dateString - ISO date string
 * @returns Formatted date string
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};
