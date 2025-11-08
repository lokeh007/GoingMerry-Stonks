"""
Screener Data Models.

Pydantic models for stock screening and analysis results.
"""

from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# Enums for categorical fields

class LynchCategory(str, Enum):
    """Peter Lynch's six stock categories."""

    FAST_GROWERS = "fast_growers"
    STALWARTS = "stalwarts"
    SLOW_GROWERS = "slow_growers"
    CYCLICALS = "cyclicals"
    TURNAROUNDS = "turnarounds"
    ASSET_PLAYS = "asset_plays"


class MarketRegime(str, Enum):
    """Market regime based on VIX levels."""

    ANY = "any"
    LOW_FEAR = "low_fear"  # VIX < 20
    MODERATE_FEAR = "moderate_fear"  # VIX 20-30
    HIGH_FEAR = "high_fear"  # VIX > 30


class RSICondition(str, Enum):
    """RSI-based conditions."""

    ANY = "any"
    OVERSOLD = "oversold"  # RSI < 30
    NEUTRAL = "neutral"  # RSI 30-70
    OVERBOUGHT = "overbought"  # RSI > 70


class MACDCondition(str, Enum):
    """MACD-based conditions."""

    ANY = "any"
    BULLISH_CROSSOVER = "bullish_crossover"
    BEARISH_CROSSOVER = "bearish_crossover"


class BulkowskiPattern(str, Enum):
    """Bulkowski chart patterns."""

    ANY = "any"
    PIPE_BOTTOM = "pipe_bottom"
    DOUBLE_BOTTOM = "double_bottom"


class GannLocation(str, Enum):
    """Position relative to Gann levels."""

    ANY = "any"
    AT_SUPPORT = "at_support"
    AT_RESISTANCE = "at_resistance"


# Data Models

class TechnicalIndicators(BaseModel):
    """Technical indicator values for a stock."""

    rsi_current: Optional[float] = Field(None, description="Current RSI value", ge=0, le=100)
    rsi_oversold: bool = Field(False, description="Is RSI oversold (< 30)")
    rsi_overbought: bool = Field(False, description="Is RSI overbought (> 70)")
    macd_bullish_crossover: bool = Field(False, description="MACD bullish crossover detected")
    macd_bearish_crossover: bool = Field(False, description="MACD bearish crossover detected")


class PatternDetection(BaseModel):
    """Chart pattern detection results."""

    pattern_name: Optional[str] = Field(None, description="Detected pattern name")
    detected: bool = Field(False, description="Pattern detected")
    confidence: int = Field(0, description="Confidence score (0-100)", ge=0, le=100)
    description: Optional[str] = Field(None, description="Pattern description")


class GannLevels(BaseModel):
    """Gann Square of 9 levels."""

    nearest_support: Optional[float] = Field(None, description="Nearest support level")
    nearest_resistance: Optional[float] = Field(None, description="Nearest resistance level")
    at_support: bool = Field(False, description="Currently at support level")
    at_resistance: bool = Field(False, description="Currently at resistance level")
    position: Optional[str] = Field(None, description="Position relative to levels")


class StockScreenerResult(BaseModel):
    """
    Model representing a single stock from a screening result.

    Attributes:
        ticker: Stock ticker symbol
        company_name: Company name
        sector: Industry sector
        market_cap: Market capitalization in billions
        price: Current stock price
        pe_ratio: Price-to-Earnings ratio
        peg_ratio: Price/Earnings to Growth ratio
        revenue_growth: Revenue growth rate (%)
        earnings_growth: Earnings growth rate (%)
        debt_to_equity: Debt-to-Equity ratio
        current_ratio: Current ratio (liquidity metric)
        score: Screening score (0-100)
        reasons: List of reasons why stock passed screening
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    market_cap: Optional[float] = Field(
        None, description="Market cap in billions", ge=0
    )

    # Pricing
    price: Optional[float] = Field(None, description="Current stock price", ge=0)

    # Valuation metrics
    pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
    peg_ratio: Optional[float] = Field(None, description="PEG ratio")

    # Growth metrics
    revenue_growth: Optional[float] = Field(None, description="Revenue growth rate (%)")
    earnings_growth: Optional[float] = Field(
        None, description="Earnings growth rate (%)"
    )

    # Financial health metrics
    debt_to_equity: Optional[float] = Field(
        None, description="Debt-to-Equity ratio", ge=0
    )
    current_ratio: Optional[float] = Field(None, description="Current ratio", ge=0)
    roe: Optional[float] = Field(None, description="Return on Equity (%)")
    institutional_ownership: Optional[float] = Field(
        None, description="Institutional ownership (%)", ge=0, le=100
    )

    # Technical indicators (optional, only included if requested)
    technical_indicators: Optional[TechnicalIndicators] = Field(
        None, description="Technical indicator values"
    )

    # Pattern detection (optional, only included if requested)
    pattern: Optional[PatternDetection] = Field(
        None, description="Chart pattern detection"
    )

    # Gann levels (optional, only included if requested)
    gann_levels: Optional[GannLevels] = Field(
        None, description="Gann Square of 9 levels"
    )

    # Screening results
    score: float = Field(..., description="Screening score (0-100)", ge=0, le=100)
    reasons: List[str] = Field(
        default_factory=list, description="Reasons why stock passed screening"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "sector": "Technology",
                "market_cap": 2800.5,
                "price": 185.92,
                "pe_ratio": 29.5,
                "peg_ratio": 2.1,
                "revenue_growth": 12.5,
                "earnings_growth": 15.8,
                "debt_to_equity": 1.73,
                "current_ratio": 1.05,
                "score": 85.5,
                "reasons": [
                    "Revenue growth > 10%",
                    "PEG ratio < 2.5",
                    "Strong financial health",
                ],
            }
        }


class ScreenerResponse(BaseModel):
    """
    Model representing the complete screening results.

    Attributes:
        screener_name: Name of the screening strategy
        description: Description of the screening criteria
        total_results: Total number of stocks that passed screening
        results: List of stocks that passed screening
        timestamp: Timestamp when screening was performed
        criteria: Screening criteria used
    """

    screener_name: str = Field(..., description="Screener strategy name")
    description: str = Field(..., description="Screener description")
    total_results: int = Field(..., description="Total number of results", ge=0)
    results: List[StockScreenerResult] = Field(
        default_factory=list, description="List of stocks that passed screening"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of screening"
    )
    criteria: Optional[dict] = Field(None, description="Screening criteria parameters")

    @field_validator("total_results", mode="before")
    @classmethod
    def calculate_total(cls, v, info):
        """Calculate total results if not provided."""
        if v is None or v == 0:
            results = info.data.get("results", [])
            return len(results)
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "screener_name": "Lynch Fast Growers",
                "description": "Peter Lynch's Fast Growers strategy",
                "total_results": 15,
                "results": [
                    {
                        "ticker": "AAPL",
                        "company_name": "Apple Inc.",
                        "sector": "Technology",
                        "market_cap": 2800.5,
                        "price": 185.92,
                        "pe_ratio": 29.5,
                        "peg_ratio": 2.1,
                        "revenue_growth": 12.5,
                        "earnings_growth": 15.8,
                        "debt_to_equity": 1.73,
                        "current_ratio": 1.05,
                        "score": 85.5,
                        "reasons": ["Revenue growth > 10%", "PEG ratio < 2.5"],
                    }
                ],
                "timestamp": "2025-01-17T10:30:00",
                "criteria": {
                    "min_earnings_growth": 10,
                    "max_peg_ratio": 2.5,
                    "min_current_ratio": 1.0,
                },
            }
        }


class ScreenerCriteria(BaseModel):
    """
    Model for screening criteria parameters.

    Attributes:
        min_earnings_growth: Minimum earnings growth rate (%)
        max_peg_ratio: Maximum PEG ratio
        min_current_ratio: Minimum current ratio
        max_debt_to_equity: Maximum debt-to-equity ratio
        min_market_cap: Minimum market cap in billions
        sectors: List of sectors to include (None = all sectors)
    """

    min_earnings_growth: Optional[float] = Field(
        10.0, description="Minimum earnings growth rate (%)", ge=0
    )
    max_peg_ratio: Optional[float] = Field(2.5, description="Maximum PEG ratio", ge=0)
    min_current_ratio: Optional[float] = Field(
        1.0, description="Minimum current ratio", ge=0
    )
    max_debt_to_equity: Optional[float] = Field(
        2.0, description="Maximum debt-to-equity ratio", ge=0
    )
    min_market_cap: Optional[float] = Field(
        1.0, description="Minimum market cap in billions", ge=0
    )
    sectors: Optional[List[str]] = Field(
        None, description="List of sectors to include (None = all)"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "min_earnings_growth": 15.0,
                "max_peg_ratio": 2.0,
                "min_current_ratio": 1.2,
                "max_debt_to_equity": 1.5,
                "min_market_cap": 2.0,
                "sectors": ["Technology", "Healthcare"],
            }
        }


class FundamentalFilters(BaseModel):
    """
    Fundamental screening filters (Lynch criteria).

    All filters are optional. If None, the filter is not applied.
    """

    max_peg_ratio: Optional[float] = Field(
        1.0, description="Maximum PEG ratio", ge=0, le=10
    )
    min_eps_growth: Optional[float] = Field(
        15.0, description="Minimum EPS growth (%)", ge=-100, le=1000
    )
    max_eps_growth: Optional[float] = Field(
        30.0, description="Maximum EPS growth (%)", ge=-100, le=1000
    )
    max_debt_to_equity: Optional[float] = Field(
        0.6, description="Maximum debt-to-equity ratio", ge=0, le=10
    )
    min_roe: Optional[float] = Field(
        15.0, description="Minimum ROE (%)", ge=-100, le=1000
    )
    max_institutional_ownership: Optional[float] = Field(
        30.0, description="Maximum institutional ownership (%)", ge=0, le=100
    )
    min_market_cap: Optional[float] = Field(
        1.0, description="Minimum market cap in billions", ge=0.001, le=10000
    )
    min_current_ratio: Optional[float] = Field(
        1.0, description="Minimum current ratio", ge=0, le=10
    )


class TechnicalFilters(BaseModel):
    """
    Technical analysis filters (Section 2: Triggers).

    All filters are optional. If set to ANY, the filter is not applied.
    """

    rsi_condition: RSICondition = Field(
        RSICondition.ANY, description="RSI condition filter"
    )
    macd_condition: MACDCondition = Field(
        MACDCondition.ANY, description="MACD condition filter"
    )
    pattern: BulkowskiPattern = Field(
        BulkowskiPattern.ANY, description="Chart pattern filter"
    )
    gann_location: GannLocation = Field(
        GannLocation.ANY, description="Gann level location filter"
    )


class AdvancedScreenerRequest(BaseModel):
    """
    Request model for advanced multi-layered stock screening.

    Combines Lynch fundamentals, technical triggers, and market context.
    """

    lynch_category: LynchCategory = Field(
        LynchCategory.FAST_GROWERS, description="Lynch stock category"
    )
    fundamental_filters: FundamentalFilters = Field(
        default_factory=FundamentalFilters, description="Fundamental screening criteria"
    )
    technical_filters: TechnicalFilters = Field(
        default_factory=TechnicalFilters, description="Technical trigger filters"
    )
    market_regime: MarketRegime = Field(
        MarketRegime.ANY, description="Market regime filter (VIX-based)"
    )
    universe: str = Field(
        "popular", description="Stock universe to screen (popular, sp500_sample, tech, nasdaq, nyse, all)"
    )
    page: int = Field(1, description="Page number for pagination", ge=1)
    page_size: int = Field(50, description="Results per page", ge=1, le=100)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "lynch_category": "fast_growers",
                "fundamental_filters": {
                    "max_peg_ratio": 1.0,
                    "min_eps_growth": 15,
                    "max_eps_growth": 30,
                    "max_debt_to_equity": 0.6,
                    "min_roe": 15,
                    "max_institutional_ownership": 30,
                },
                "technical_filters": {
                    "rsi_condition": "oversold",
                    "macd_condition": "bullish_crossover",
                    "pattern": "pipe_bottom",
                    "gann_location": "at_support",
                },
                "market_regime": "high_fear",
                "universe": "popular",
                "page": 1,
                "page_size": 50,
            }
        }
