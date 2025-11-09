/**
 * Stock Screener Type Definitions
 *
 * TypeScript interfaces matching the backend Pydantic models for the screener API
 */

// ============================================================================
// ENUMS (matching backend enums)
// ============================================================================

export enum LynchCategory {
  FAST_GROWERS = 'fast_growers',
  STALWARTS = 'stalwarts',
  SLOW_GROWERS = 'slow_growers',
  CYCLICALS = 'cyclicals',
  TURNAROUNDS = 'turnarounds',
  ASSET_PLAYS = 'asset_plays',
}

export enum MarketRegime {
  ANY = 'any',
  LOW_FEAR = 'low_fear',
  MODERATE_FEAR = 'moderate_fear',
  HIGH_FEAR = 'high_fear',
}

export enum RSICondition {
  ANY = 'any',
  OVERSOLD = 'oversold',
  NEUTRAL = 'neutral',
  OVERBOUGHT = 'overbought',
}

export enum MACDCondition {
  ANY = 'any',
  BULLISH_CROSSOVER = 'bullish_crossover',
  BEARISH_CROSSOVER = 'bearish_crossover',
}

export enum BulkowskiPattern {
  ANY = 'any',
  PIPE_BOTTOM = 'pipe_bottom',
  DOUBLE_BOTTOM = 'double_bottom',
}

export enum GannLocation {
  ANY = 'any',
  AT_SUPPORT = 'at_support',
  AT_RESISTANCE = 'at_resistance',
}

// ============================================================================
// FILTER INTERFACES
// ============================================================================

export interface FundamentalFilters {
  max_peg_ratio?: number;
  min_eps_growth?: number;
  max_eps_growth?: number;
  max_debt_to_equity?: number;
  min_roe?: number;
  max_institutional_ownership?: number;
  min_market_cap?: number;
  min_current_ratio?: number;
}

export interface TechnicalFilters {
  rsi_condition?: RSICondition;
  macd_condition?: MACDCondition;
  pattern?: BulkowskiPattern;
  gann_location?: GannLocation;
}

// ============================================================================
// REQUEST/RESPONSE MODELS
// ============================================================================

export interface AdvancedScreenerRequest {
  lynch_category: LynchCategory;
  fundamental_filters?: FundamentalFilters;
  technical_filters?: TechnicalFilters;
  market_regime?: MarketRegime;
  universe?: string;
  page?: number;
  page_size?: number;
}

export interface TechnicalIndicators {
  rsi_current?: number;
  rsi_oversold: boolean;
  rsi_overbought: boolean;
  macd_bullish_crossover: boolean;
  macd_bearish_crossover: boolean;
}

export interface PatternDetection {
  pattern_name?: string;
  detected: boolean;
  confidence: number;
  description?: string;
}

export interface GannLevels {
  nearest_support?: number;
  nearest_resistance?: number;
  at_support: boolean;
  at_resistance: boolean;
  position?: string;
}

export interface StockScreenerResult {
  ticker: string;
  company_name: string;
  sector: string;
  market_cap?: number;
  price?: number;
  pe_ratio?: number;
  peg_ratio?: number;
  revenue_growth?: number;
  earnings_growth?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  roe?: number;
  institutional_ownership?: number;
  technical_indicators?: TechnicalIndicators;
  pattern?: PatternDetection;
  gann_levels?: GannLevels;
  score: number;
  reasons: string[];
}

export interface ScreenerResponse {
  screener_name: string;
  description: string;
  total_results: number;
  results: StockScreenerResult[];
  timestamp: string;
  criteria: AdvancedScreenerRequest;
}

// ============================================================================
// CATEGORY PRESET INTERFACES
// ============================================================================

export interface CategoryPreset {
  category: string;
  name: string;
  filters: FundamentalFilters;
  ideal_for: string;
  risk_level: string;
  holding_period: string;
  philosophy: string;
}

// ============================================================================
// VIX DATA INTERFACE
// ============================================================================

export interface VixData {
  value: number;
  regime: string;
  regime_label: string;
  timestamp: string;
}

// ============================================================================
// DISPLAY HELPERS
// ============================================================================

export const LynchCategoryLabels: Record<LynchCategory, string> = {
  [LynchCategory.FAST_GROWERS]: 'Fast Growers',
  [LynchCategory.STALWARTS]: 'Stalwarts',
  [LynchCategory.SLOW_GROWERS]: 'Slow Growers',
  [LynchCategory.CYCLICALS]: 'Cyclicals',
  [LynchCategory.TURNAROUNDS]: 'Turnarounds',
  [LynchCategory.ASSET_PLAYS]: 'Asset Plays',
};

export const MarketRegimeLabels: Record<MarketRegime, string> = {
  [MarketRegime.ANY]: 'Any Market',
  [MarketRegime.LOW_FEAR]: 'Low Fear (VIX < 20)',
  [MarketRegime.MODERATE_FEAR]: 'Moderate Fear (VIX 20-30)',
  [MarketRegime.HIGH_FEAR]: 'High Fear (VIX > 30)',
};

// ============================================================================
// DEFAULT VALUES
// ============================================================================

export const DEFAULT_FUNDAMENTAL_FILTERS: FundamentalFilters = {
  max_peg_ratio: 1.0,
  min_eps_growth: 15,
  max_eps_growth: 30,
  max_debt_to_equity: 0.6,
  min_roe: 15,
  max_institutional_ownership: 30,
};

export const DEFAULT_TECHNICAL_FILTERS: TechnicalFilters = {
  rsi_condition: RSICondition.ANY,
  macd_condition: MACDCondition.ANY,
  pattern: BulkowskiPattern.ANY,
  gann_location: GannLocation.ANY,
};
