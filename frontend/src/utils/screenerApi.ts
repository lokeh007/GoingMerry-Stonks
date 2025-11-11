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
  const response = await apiClient.get<any>('/screener/screeners');
  return response.data.screeners || [];
};

/**
 * Run Smart Money screener (options-driven)
 *
 * @param params - Screening parameters
 * @returns Promise resolving to screener response with results
 */
export const runSmartMoneyScreener = async (params: {
  min_call_to_put_ratio?: number;
  unusual_volume_multiplier?: number;
  universe?: string;
}): Promise<ScreenerResponse> => {
  const queryParams = new URLSearchParams();

  if (params.min_call_to_put_ratio !== undefined) {
    queryParams.append('min_call_to_put_ratio', params.min_call_to_put_ratio.toString());
  }
  if (params.unusual_volume_multiplier !== undefined) {
    queryParams.append('unusual_volume_multiplier', params.unusual_volume_multiplier.toString());
  }
  if (params.universe) {
    queryParams.append('universe', params.universe);
  }

  const url = `/screener/smart-money?${queryParams.toString()}`;
  const response = await apiClient.get<ScreenerResponse>(url);
  return response.data;
};

/**
 * Run The Undiscovered screener (Lynch-inspired)
 *
 * @param params - Screening parameters
 * @returns Promise resolving to screener response with results
 */
export const runUndiscoveredScreener = async (params: {
  max_institutional_ownership?: number;
  max_analyst_coverage?: number;
  require_insider_buying?: boolean;
  universe?: string;
}): Promise<ScreenerResponse> => {
  const queryParams = new URLSearchParams();

  if (params.max_institutional_ownership !== undefined) {
    queryParams.append('max_institutional_ownership', params.max_institutional_ownership.toString());
  }
  if (params.max_analyst_coverage !== undefined) {
    queryParams.append('max_analyst_coverage', params.max_analyst_coverage.toString());
  }
  if (params.require_insider_buying !== undefined) {
    queryParams.append('require_insider_buying', params.require_insider_buying.toString());
  }
  if (params.universe) {
    queryParams.append('universe', params.universe);
  }

  const url = `/screener/the-undiscovered?${queryParams.toString()}`;
  const response = await apiClient.get<ScreenerResponse>(url);
  return response.data;
};

/**
 * Run The Coiled Spring screener (Bulkowski-inspired)
 *
 * @param params - Screening parameters
 * @returns Promise resolving to screener response with results
 */
export const runCoiledSpringScreener = async (params: {
  max_volatility_30d?: number;
  require_nr7?: boolean;
  min_percentile_rank?: number;
  universe?: string;
}): Promise<ScreenerResponse> => {
  const queryParams = new URLSearchParams();

  if (params.max_volatility_30d !== undefined) {
    queryParams.append('max_volatility_30d', params.max_volatility_30d.toString());
  }
  if (params.require_nr7 !== undefined) {
    queryParams.append('require_nr7', params.require_nr7.toString());
  }
  if (params.min_percentile_rank !== undefined) {
    queryParams.append('min_percentile_rank', params.min_percentile_rank.toString());
  }
  if (params.universe) {
    queryParams.append('universe', params.universe);
  }

  const url = `/screener/coiled-spring?${queryParams.toString()}`;
  const response = await apiClient.get<ScreenerResponse>(url);
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
