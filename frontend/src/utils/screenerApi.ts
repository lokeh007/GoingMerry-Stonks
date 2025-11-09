/**
 * Stock Screener API Client
 *
 * Utility functions for calling the screener API endpoints
 */

import { apiClient } from '../config/api';
import {
  AdvancedScreenerRequest,
  ScreenerResponse,
  CategoryPreset,
  VixData,
  LynchCategory,
} from '../types/screener';

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * Run advanced multi-layered stock screening
 *
 * @param request - Screening criteria including filters and pagination
 * @returns Promise resolving to screener response with results
 */
export const runAdvancedScreener = async (
  request: AdvancedScreenerRequest
): Promise<ScreenerResponse> => {
  const response = await apiClient.post<ScreenerResponse>('/screener/advanced', request);
  return response.data;
};

/**
 * Get recommended filter presets for a Lynch category
 *
 * @param category - Lynch stock category (fast_growers, stalwarts, etc.)
 * @returns Promise resolving to category preset configuration
 */
export const getCategoryPreset = async (category: LynchCategory): Promise<CategoryPreset> => {
  const response = await apiClient.get<CategoryPreset>(`/screener/presets/${category}`);
  return response.data;
};

/**
 * Get current VIX (market volatility) data
 *
 * @returns Promise resolving to VIX value and market regime classification
 */
export const getVixData = async (): Promise<VixData> => {
  const response = await apiClient.get<VixData>('/screener/vix');
  return response.data;
};

/**
 * Get list of available screeners
 *
 * @returns Promise resolving to array of screener metadata
 */
export const getAvailableScreeners = async (): Promise<any[]> => {
  const response = await apiClient.get<any[]>('/screener/screeners');
  return response.data;
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Build URL parameters for sharing screener configuration
 *
 * @param request - Screening criteria to encode
 * @returns URL search params string
 */
export const buildScreenerURLParams = (request: AdvancedScreenerRequest): string => {
  const params = new URLSearchParams();

  // Add category
  params.set('category', request.lynch_category);

  // Add fundamental filters
  if (request.fundamental_filters) {
    Object.entries(request.fundamental_filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.set(key, value.toString());
      }
    });
  }

  // Add technical filters
  if (request.technical_filters) {
    Object.entries(request.technical_filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== 'any') {
        params.set(key, value.toString());
      }
    });
  }

  // Add market regime
  if (request.market_regime && request.market_regime !== 'any') {
    params.set('market_regime', request.market_regime);
  }

  // Add pagination
  if (request.page) {
    params.set('page', request.page.toString());
  }

  return params.toString();
};

/**
 * Parse URL parameters to reconstruct screener request
 *
 * @param searchParams - URL search params from location
 * @returns Partial screener request object
 */
export const parseScreenerURLParams = (searchParams: URLSearchParams): Partial<AdvancedScreenerRequest> => {
  const request: Partial<AdvancedScreenerRequest> = {
    fundamental_filters: {},
    technical_filters: {},
  };

  // Parse category
  const category = searchParams.get('category');
  if (category) {
    request.lynch_category = category as LynchCategory;
  }

  // Parse fundamental filters
  const fundamentalKeys = ['max_peg_ratio', 'min_eps_growth', 'max_eps_growth', 'max_debt_to_equity', 'min_roe', 'max_institutional_ownership', 'min_market_cap', 'min_current_ratio'];
  fundamentalKeys.forEach(key => {
    const value = searchParams.get(key);
    if (value && request.fundamental_filters) {
      request.fundamental_filters[key as keyof typeof request.fundamental_filters] = parseFloat(value);
    }
  });

  // Parse technical filters
  const rsiCondition = searchParams.get('rsi_condition');
  if (rsiCondition && request.technical_filters) {
    request.technical_filters.rsi_condition = rsiCondition as any;
  }

  const macdCondition = searchParams.get('macd_condition');
  if (macdCondition && request.technical_filters) {
    request.technical_filters.macd_condition = macdCondition as any;
  }

  const pattern = searchParams.get('pattern');
  if (pattern && request.technical_filters) {
    request.technical_filters.pattern = pattern as any;
  }

  const gannLocation = searchParams.get('gann_location');
  if (gannLocation && request.technical_filters) {
    request.technical_filters.gann_location = gannLocation as any;
  }

  // Parse market regime
  const marketRegime = searchParams.get('market_regime');
  if (marketRegime) {
    request.market_regime = marketRegime as any;
  }

  // Parse pagination
  const page = searchParams.get('page');
  if (page) {
    request.page = parseInt(page);
  }

  return request;
};
