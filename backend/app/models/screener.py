"""
Screener Data Models.

Pydantic models for stock screening and analysis results.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


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
    market_cap: Optional[float] = Field(None, description="Market cap in billions", ge=0)

    # Pricing
    price: Optional[float] = Field(None, description="Current stock price", ge=0)

    # Valuation metrics
    pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
    peg_ratio: Optional[float] = Field(None, description="PEG ratio")

    # Growth metrics
    revenue_growth: Optional[float] = Field(None, description="Revenue growth rate (%)")
    earnings_growth: Optional[float] = Field(None, description="Earnings growth rate (%)")

    # Financial health metrics
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-Equity ratio", ge=0)
    current_ratio: Optional[float] = Field(None, description="Current ratio", ge=0)

    # Screening results
    score: float = Field(..., description="Screening score (0-100)", ge=0, le=100)
    reasons: List[str] = Field(
        default_factory=list,
        description="Reasons why stock passed screening"
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
                    "Strong financial health"
                ]
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
        default_factory=list,
        description="List of stocks that passed screening"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of screening"
    )
    criteria: Optional[dict] = Field(
        None,
        description="Screening criteria parameters"
    )

    @field_validator('total_results', mode='before')
    @classmethod
    def calculate_total(cls, v, info):
        """Calculate total results if not provided."""
        if v is None or v == 0:
            results = info.data.get('results', [])
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
                        "reasons": [
                            "Revenue growth > 10%",
                            "PEG ratio < 2.5"
                        ]
                    }
                ],
                "timestamp": "2025-01-17T10:30:00",
                "criteria": {
                    "min_earnings_growth": 10,
                    "max_peg_ratio": 2.5,
                    "min_current_ratio": 1.0
                }
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
        10.0,
        description="Minimum earnings growth rate (%)",
        ge=0
    )
    max_peg_ratio: Optional[float] = Field(
        2.5,
        description="Maximum PEG ratio",
        ge=0
    )
    min_current_ratio: Optional[float] = Field(
        1.0,
        description="Minimum current ratio",
        ge=0
    )
    max_debt_to_equity: Optional[float] = Field(
        2.0,
        description="Maximum debt-to-equity ratio",
        ge=0
    )
    min_market_cap: Optional[float] = Field(
        1.0,
        description="Minimum market cap in billions",
        ge=0
    )
    sectors: Optional[List[str]] = Field(
        None,
        description="List of sectors to include (None = all)"
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
                "sectors": ["Technology", "Healthcare"]
            }
        }
