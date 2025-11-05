/**
 * TypeScript type definitions for options data.
 *
 * These interfaces match the backend Pydantic models for type safety
 * across the full stack.
 */

/**
 * Option contract type
 */
export type OptionType = 'call' | 'put';

/**
 * Individual option contract
 */
export interface OptionContract {
  ticker: string;
  strike: number;
  expiration_date: string;
  option_type: OptionType;
  last_price?: number;
  bid?: number;
  ask?: number;
  volume?: number;
  open_interest?: number;
  implied_volatility?: number;
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  last_updated?: string;
}

/**
 * Complete option chain response from API
 */
export interface OptionChainResponse {
  ticker: string;
  stock_price: number;
  calls: OptionContract[];
  puts: OptionContract[];
  total_contracts: number;
  available_expirations?: string[];
  timestamp: string;
  note?: string;
}

/**
 * Grid cell data for rendering
 */
export interface GridCellData {
  strike: number;
  expiration: string;
  netCredit: number | null;
  callBid?: number;
  callAsk?: number;
  putBid?: number;
  putAsk?: number;
  call?: OptionContract;
  put?: OptionContract;
}

/**
 * Organized grid data structure
 */
export interface GridData {
  ticker: string;
  stockPrice: number;
  strikes: number[];
  expirations: string[];
  cells: Map<string, GridCellData>;
}
