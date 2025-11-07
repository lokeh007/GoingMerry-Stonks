"""
Options Router Module.

This module defines API endpoints for options-related operations,
including retrieving option chains and analyzing option contracts.
"""

from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from ..services.market_data import (
    MarketDataProvider,
    MarketDataError,
    InvalidTickerError,
    APIConnectionError,
    RateLimitError,
)
from ..models.options import OptionChainResponse, OptionContract, OptionType


# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/options",
    tags=["Options"],
    responses={
        404: {"description": "Ticker not found or no options available"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)

# Initialize market data provider (singleton pattern)
market_data_provider = MarketDataProvider()


@router.get(
    "/{ticker}",
    response_model=OptionChainResponse,
    summary="Get Option Chain",
    description="Retrieve the complete option chain for a given stock ticker symbol.",
)
async def get_option_chain(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol (e.g., AAPL, TSLA)",
        min_length=1,
        max_length=10,
        pattern="^[A-Z]+$",
    ),
    expiration_date: Optional[str] = Query(
        None,
        description="Filter by expiration date (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    atm_strikes: Optional[int] = Query(
        None,
        description="Number of strikes to show around ATM price (e.g., 5 = 5 above + 5 below)",
        ge=1,
        le=50,
    ),
    limit: int = Query(
        250,
        description="Maximum number of contracts to return",
        ge=1,
        le=1000,
    ),
) -> OptionChainResponse:
    """
    Get the option chain for a specific ticker.

    This endpoint retrieves all available option contracts (calls and puts)
    for the specified underlying stock ticker, including pricing data and Greeks.

    **Parameters:**
    - **ticker**: Stock ticker symbol (automatically converted to uppercase)
    - **expiration_date**: Optional filter for specific expiration date
    - **limit**: Maximum number of contracts to return (default: 50, max: 250)

    **Returns:**
    - Option chain data including:
        - Current stock price
        - List of call option contracts
        - List of put option contracts
        - Total contract count
        - Timestamp of the data

    **Example Request:**
    ```
    GET /options/AAPL
    GET /options/AAPL?expiration_date=2025-01-17
    GET /options/TSLA?limit=100
    ```

    **Example Response:**
    ```json
    {
        "ticker": "AAPL",
        "stock_price": 150.25,
        "calls": [...],
        "puts": [...],
        "total_contracts": 50,
        "timestamp": "2025-01-17T10:30:00"
    }
    ```
    """
    try:
        logger.info(
            f"Received option chain request for {ticker} "
            f"(expiration: {expiration_date}, limit: {limit})"
        )

        # Fetch option chain data
        chain_data = market_data_provider.get_option_chain(
            ticker=ticker.upper(),
            expiration_date=expiration_date,
            atm_strikes=atm_strikes,
            limit=limit,
        )

        # Parse contracts into Pydantic models
        calls = [
            OptionContract(
                ticker=contract.get("ticker", ""),
                strike=contract.get("strike", 0.0),
                expiration_date=contract.get("expiration_date", ""),
                option_type=OptionType.CALL,
                last_price=contract.get("last_price"),
                bid=contract.get("bid"),
                ask=contract.get("ask"),
                volume=contract.get("volume"),
                open_interest=contract.get("open_interest"),
                implied_volatility=contract.get("implied_volatility"),
                delta=contract.get("delta"),
                gamma=contract.get("gamma"),
                theta=contract.get("theta"),
                vega=contract.get("vega"),
                last_updated=datetime.now(),
            )
            for contract in chain_data.get("calls", [])
        ]

        puts = [
            OptionContract(
                ticker=contract.get("ticker", ""),
                strike=contract.get("strike", 0.0),
                expiration_date=contract.get("expiration_date", ""),
                option_type=OptionType.PUT,
                last_price=contract.get("last_price"),
                bid=contract.get("bid"),
                ask=contract.get("ask"),
                volume=contract.get("volume"),
                open_interest=contract.get("open_interest"),
                implied_volatility=contract.get("implied_volatility"),
                delta=contract.get("delta"),
                gamma=contract.get("gamma"),
                theta=contract.get("theta"),
                vega=contract.get("vega"),
                last_updated=datetime.now(),
            )
            for contract in chain_data.get("puts", [])
        ]

        # Create response
        response = OptionChainResponse(
            ticker=chain_data["ticker"],
            stock_price=chain_data["stock_price"],
            calls=calls,
            puts=puts,
            total_contracts=len(calls) + len(puts),
            available_expirations=chain_data.get("available_expirations", []),
            timestamp=datetime.now(),
        )

        logger.info(
            f"Successfully retrieved option chain for {ticker}: "
            f"{len(calls)} calls, {len(puts)} puts"
        )

        return response

    except InvalidTickerError as e:
        logger.warning(f"Invalid ticker requested: {ticker}")
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker}' not found or has no listed options. {str(e)}",
        )

    except RateLimitError:
        logger.error(f"Rate limit exceeded for ticker: {ticker}")
        raise HTTPException(
            status_code=429,
            detail="API rate limit exceeded. Please try again later.",
        )

    except APIConnectionError as e:
        logger.error(f"API connection error for {ticker}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to market data service. {str(e)}",
        )

    except MarketDataError as e:
        logger.error(f"Market data error for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving market data. {str(e)}",
        )

    except Exception:
        logger.exception(f"Unexpected error retrieving option chain for {ticker}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/{ticker}/summary",
    summary="Get Option Chain Summary",
    description="Get a summary of option chain statistics for a ticker.",
)
async def get_option_chain_summary(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol",
        min_length=1,
        max_length=10,
    ),
):
    """
    Get a summary of option chain statistics.

    This endpoint provides aggregate statistics about the option chain,
    useful for quick analysis without retrieving all contract details.

    **Returns:**
    - Summary statistics including:
        - Total number of call/put contracts
        - Volume statistics
        - Open interest totals
        - Price ranges
    """
    try:
        # Fetch option chain data
        chain_data = market_data_provider.get_option_chain(
            ticker=ticker.upper(),
            limit=250,
        )

        calls = chain_data.get("calls", [])
        puts = chain_data.get("puts", [])

        # Calculate summary statistics
        summary = {
            "ticker": chain_data["ticker"],
            "stock_price": chain_data["stock_price"],
            "total_contracts": len(calls) + len(puts),
            "calls_count": len(calls),
            "puts_count": len(puts),
            "total_volume": sum(
                c.get("volume", 0) for c in calls + puts if c.get("volume")
            ),
            "total_open_interest": sum(
                c.get("open_interest", 0)
                for c in calls + puts
                if c.get("open_interest")
            ),
            "call_put_ratio": (len(calls) / len(puts) if len(puts) > 0 else None),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Generated option chain summary for {ticker}")
        return JSONResponse(content=summary)

    except InvalidTickerError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except APIConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception(f"Error generating summary for {ticker}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/market/vix",
    summary="Get VIX (Volatility Index)",
    description="Get the current VIX value from Yahoo Finance.",
)
async def get_vix():
    """
    Get the current VIX (Volatility Index) value.

    The VIX measures the market's expectation of 30-day forward-looking volatility
    derived from S&P 500 index options. Higher values indicate higher expected volatility.

    **Interpretation:**
    - VIX < 18: Low volatility (stable market conditions)
    - VIX 18-20: Moderate volatility
    - VIX > 20: High volatility (uncertain/volatile market conditions)

    **Returns:**
    - VIX value and timestamp

    **Example Response:**
    ```json
    {
        "value": 15.42,
        "timestamp": "2025-11-05T10:30:00"
    }
    ```
    """
    try:
        logger.info("Received VIX request")

        # Fetch VIX data
        vix_data = market_data_provider.get_vix()

        logger.info(f"Successfully retrieved VIX: {vix_data['value']:.2f}")
        return JSONResponse(content=vix_data)

    except MarketDataError as e:
        logger.error(f"Error fetching VIX: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving VIX data. {str(e)}",
        )

    except Exception:
        logger.exception("Unexpected error retrieving VIX")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )
