/**
 * Gann Square of 9 Type Definitions
 *
 * Type definitions for Gann Square of 9 calculations and API responses.
 */

export interface GannLevelsResponse {
  ticker: string;
  current_price: number;
  reference_price: number;
  week_52_low?: number;
  week_52_high?: number;
  support_levels: number[];
  resistance_levels: number[];
  nearest_support: number | null;
  nearest_resistance: number | null;
  current_position: 'at_support' | 'at_resistance' | 'between_levels' | 'unknown';
  at_key_level: {
    at_support: boolean;
    at_resistance: boolean;
  };
  num_levels_calculated: number;
}

export interface GannCalculationParams {
  ticker: string;
  reference_price?: number;
  num_levels?: number;
}
