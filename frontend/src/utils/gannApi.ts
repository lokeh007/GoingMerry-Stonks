/**
 * Gann Square of 9 API Client
 *
 * Utility functions for interacting with the Gann Square of 9 API endpoints.
 */

import { apiClient } from '../config/api';
import { GannLevelsResponse, GannCalculationParams } from '../types/gann';

/**
 * Fetch Gann Square of 9 levels for a ticker
 *
 * @param params - Calculation parameters (ticker, reference_price, num_levels)
 * @returns Promise resolving to Gann levels data
 */
export async function fetchGannLevels(
  params: GannCalculationParams
): Promise<GannLevelsResponse> {
  const { ticker, reference_price, num_levels = 5 } = params;

  const queryParams = new URLSearchParams();
  if (reference_price) {
    queryParams.append('reference_price', reference_price.toString());
  }
  queryParams.append('num_levels', num_levels.toString());

  const url = `/technical/${ticker.toUpperCase()}/gann?${queryParams.toString()}`;

  const response = await apiClient.get<GannLevelsResponse>(url);
  return response.data;
}
