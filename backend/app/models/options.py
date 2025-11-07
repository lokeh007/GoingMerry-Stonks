"""
Options Data Models.

Pydantic models for options data validation and serialization.
"""

from enum import Enum
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator


class OptionType(str, Enum):
    """Option contract type enumeration."""

    CALL = "call"
    PUT = "put"


class OptionContract(BaseModel):
    """
    Model representing a single option contract.

    Attributes:
        ticker: Option contract ticker symbol (e.g., 'AAPL250117C00150000')
        strike: Strike price of the option
        expiration_date: Expiration date (YYYY-MM-DD)
        option_type: Type of option (call or put)
        last_price: Last traded price
        bid: Current bid price
        ask: Current ask price
        volume: Trading volume
        open_interest: Number of outstanding contracts
        implied_volatility: Implied volatility (if available)
        delta: Delta Greek (if available)
        gamma: Gamma Greek (if available)
        theta: Theta Greek (if available)
        vega: Vega Greek (if available)
    """

    ticker: str = Field(..., description="Option contract ticker symbol")
    strike: float = Field(..., gt=0, description="Strike price")
    expiration_date: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    option_type: OptionType = Field(..., description="Option type (call/put)")

    # Pricing data
    last_price: Optional[float] = Field(None, ge=0, description="Last traded price")
    bid: Optional[float] = Field(None, ge=0, description="Bid price")
    ask: Optional[float] = Field(None, ge=0, description="Ask price")
    volume: Optional[int] = Field(None, ge=0, description="Trading volume")
    open_interest: Optional[int] = Field(None, ge=0, description="Open interest")

    # Greeks
    implied_volatility: Optional[float] = Field(
        None, ge=0, description="Implied volatility"
    )
    delta: Optional[float] = Field(None, description="Delta Greek")
    gamma: Optional[float] = Field(None, description="Gamma Greek")
    theta: Optional[float] = Field(None, description="Theta Greek")
    vega: Optional[float] = Field(None, description="Vega Greek")

    # Additional fields
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "ticker": "AAPL250117C00150000",
                "strike": 150.0,
                "expiration_date": "2025-01-17",
                "option_type": "call",
                "last_price": 5.25,
                "bid": 5.20,
                "ask": 5.30,
                "volume": 1250,
                "open_interest": 5000,
                "implied_volatility": 0.25,
                "delta": 0.65,
                "gamma": 0.035,
                "theta": -0.05,
                "vega": 0.15,
            }
        }


class OptionChainResponse(BaseModel):
    """
    Model representing the full option chain for a ticker.

    Attributes:
        ticker: Underlying stock ticker symbol
        stock_price: Current stock price
        calls: List of call option contracts
        puts: List of put option contracts
        total_contracts: Total number of contracts returned
        available_expirations: List of available expiration dates
        timestamp: Timestamp of the data
        note: Optional informational message (e.g., free-tier limitations)
    """

    ticker: str = Field(..., description="Underlying stock ticker")
    stock_price: float = Field(..., gt=0, description="Current stock price")
    calls: List[OptionContract] = Field(
        default_factory=list, description="Call options"
    )
    puts: List[OptionContract] = Field(default_factory=list, description="Put options")
    total_contracts: int = Field(..., ge=0, description="Total number of contracts")
    available_expirations: List[str] = Field(
        default_factory=list, description="Available expiration dates (YYYY-MM-DD)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Data timestamp"
    )
    note: Optional[str] = Field(
        None, description="Informational message about data limitations"
    )

    @field_validator("total_contracts", mode="before")
    @classmethod
    def calculate_total(cls, v, info):
        """Calculate total contracts if not provided."""
        if v is None or v == 0:
            calls = info.data.get("calls", [])
            puts = info.data.get("puts", [])
            return len(calls) + len(puts)
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "stock_price": 150.25,
                "calls": [
                    {
                        "ticker": "AAPL250117C00150000",
                        "strike": 150.0,
                        "expiration_date": "2025-01-17",
                        "option_type": "call",
                        "last_price": 5.25,
                        "bid": 5.20,
                        "ask": 5.30,
                        "volume": 1250,
                        "open_interest": 5000,
                    }
                ],
                "puts": [
                    {
                        "ticker": "AAPL250117P00150000",
                        "strike": 150.0,
                        "expiration_date": "2025-01-17",
                        "option_type": "put",
                        "last_price": 4.75,
                        "bid": 4.70,
                        "ask": 4.80,
                        "volume": 980,
                        "open_interest": 4200,
                    }
                ],
                "total_contracts": 2,
                "timestamp": "2025-01-17T10:30:00",
            }
        }
