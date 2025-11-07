"""
Technical Analysis Router Module.

This module defines API endpoints for technical analysis operations,
including retrieving price history and calculating technical indicators.
"""

from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from ..services.technical_analysis import (
    TechnicalAnalysisProvider,
    TechnicalAnalysisError,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/technical",
    tags=["Technical Analysis"],
    responses={
        404: {"description": "Ticker not found or no data available"},
        500: {"description": "Internal server error"},
    },
)

# Initialize technical analysis provider (singleton pattern)
technical_provider = TechnicalAnalysisProvider()


@router.get(
    "/{ticker}",
    summary="Get Technical Analysis",
    description="Get comprehensive technical analysis data including price history and indicators.",
)
async def get_technical_analysis(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol (e.g., AAPL, TSLA)",
        min_length=1,
        max_length=10,
        pattern="^[A-Z]+$",
    ),
    period: str = Query(
        "6mo",
        description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
    ),
    interval: str = Query(
        "1d",
        description="Data interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo",
    ),
    indicators: Optional[str] = Query(
        None,
        description=(
            "Comma-separated list of indicators (e.g., 'rsi,macd,ema12'). "
            "Leave empty for all."
        ),
    ),
):
    """
    Get technical analysis data for a specific ticker.

    This endpoint retrieves historical price data and calculates
    various technical indicators including RSI, MACD, EMAs, SMAs,
    and Bollinger Bands.

    **Parameters:**
    - **ticker**: Stock ticker symbol (automatically converted to uppercase)
    - **period**: Time period for historical data (default: 6mo)
    - **interval**: Data interval (default: 1d for daily)
    - **indicators**: Comma-separated list of indicators to calculate

    **Available Indicators:**
    - rsi: Relative Strength Index (14-period)
    - macd: Moving Average Convergence Divergence
    - ema12, ema26, ema50, ema200: Exponential Moving Averages
    - sma20, sma50, sma200: Simple Moving Averages
    - bollinger: Bollinger Bands

    **Returns:**
    - Price history (OHLCV data)
    - Calculated technical indicators
    - Current indicator values
    - Metadata (data points, timestamp)

    **Example Request:**
    ```
    GET /technical/AAPL
    GET /technical/AAPL?period=1y&interval=1d
    GET /technical/TSLA?indicators=rsi,macd,ema50
    ```

    **Example Response:**
    ```json
    {
        "ticker": "AAPL",
        "period": "6mo",
        "interval": "1d",
        "data_points": 126,
        "price_data": {
            "dates": ["2024-05-01", "2024-05-02", ...],
            "close": [170.23, 171.45, ...]
        },
        "indicators": {
            "rsi": [65.3, 67.2, ...],
            "rsi_current": 67.2,
            "macd": {
                "macd_line": [2.3, 2.5, ...],
                "signal_line": [2.1, 2.3, ...],
                "histogram": [0.2, 0.2, ...]
            }
        },
        "timestamp": "2025-11-05T10:30:00"
    }
    ```
    """
    try:
        logger.info(
            f"Received technical analysis request for {ticker} "
            f"(period={period}, interval={interval}, indicators={indicators})"
        )

        # Parse indicators if provided
        indicator_list = None
        if indicators:
            indicator_list = [ind.strip() for ind in indicators.split(",")]

        # Get technical analysis data
        analysis_data = technical_provider.get_technical_analysis(
            ticker=ticker.upper(),
            period=period,
            interval=interval,
            indicators=indicator_list,
        )

        logger.info(
            f"Successfully generated technical analysis for {ticker}: "
            f"{analysis_data['data_points']} data points"
        )

        return JSONResponse(content=analysis_data)

    except TechnicalAnalysisError as e:
        logger.error(f"Technical analysis error for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating technical analysis. {str(e)}",
        )

    except Exception:
        logger.exception(f"Unexpected error in technical analysis for {ticker}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/{ticker}/rsi",
    summary="Get RSI Only",
    description="Get Relative Strength Index for a ticker.",
)
async def get_rsi(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol",
        min_length=1,
        max_length=10,
    ),
    period: str = Query(
        "6mo",
        description="Time period for historical data",
    ),
    rsi_period: int = Query(
        14,
        description="RSI calculation period (default: 14)",
        ge=2,
        le=50,
    ),
):
    """
    Get RSI (Relative Strength Index) data for a ticker.

    RSI is a momentum oscillator that measures the speed and magnitude
    of recent price changes. Values range from 0 to 100.

    **Interpretation:**
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    - RSI = 50: Neutral

    **Returns:**
    - Historical RSI values
    - Current RSI value
    - Overbought/oversold status
    """
    try:
        logger.info(f"Received RSI request for {ticker}")

        # Get price history
        hist = technical_provider.get_price_history(ticker.upper(), period=period)

        # Calculate RSI
        rsi_values = technical_provider.calculate_rsi(hist["Close"], period=rsi_period)

        # Get current RSI
        current_rsi = float(rsi_values.iloc[-1]) if not rsi_values.empty else None

        # Determine status
        status = "neutral"
        if current_rsi is not None:
            if current_rsi > 70:
                status = "overbought"
            elif current_rsi < 30:
                status = "oversold"

        result = {
            "ticker": ticker.upper(),
            "period": period,
            "rsi_period": rsi_period,
            "current_rsi": current_rsi,
            "status": status,
            "rsi_values": rsi_values.fillna(0).tolist(),
            "dates": hist.index.strftime("%Y-%m-%d").tolist(),
            "timestamp": technical_provider.get_price_history(
                ticker, period
            ).__class__.__name__,
        }

        logger.info(f"Successfully calculated RSI for {ticker}: {current_rsi:.2f}")
        return JSONResponse(content=result)

    except TechnicalAnalysisError as e:
        logger.error(f"Error calculating RSI for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception:
        logger.exception(f"Unexpected error calculating RSI for {ticker}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{ticker}/macd",
    summary="Get MACD Only",
    description="Get MACD indicator for a ticker.",
)
async def get_macd(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol",
        min_length=1,
        max_length=10,
    ),
    period: str = Query(
        "6mo",
        description="Time period for historical data",
    ),
):
    """
    Get MACD (Moving Average Convergence Divergence) data for a ticker.

    MACD is a trend-following momentum indicator that shows the
    relationship between two moving averages.

    **Components:**
    - MACD Line: 12-day EMA - 26-day EMA
    - Signal Line: 9-day EMA of MACD Line
    - Histogram: MACD Line - Signal Line

    **Signals:**
    - MACD crosses above Signal: Bullish signal
    - MACD crosses below Signal: Bearish signal
    """
    try:
        logger.info(f"Received MACD request for {ticker}")

        # Get price history
        hist = technical_provider.get_price_history(ticker.upper(), period=period)

        # Calculate MACD
        macd_data = technical_provider.calculate_macd(hist["Close"])

        result = {
            "ticker": ticker.upper(),
            "period": period,
            "macd": {
                "macd_line": macd_data["macd"].fillna(0).tolist(),
                "signal_line": macd_data["signal"].fillna(0).tolist(),
                "histogram": macd_data["histogram"].fillna(0).tolist(),
            },
            "current": {
                "macd": float(macd_data["macd"].iloc[-1]),
                "signal": float(macd_data["signal"].iloc[-1]),
                "histogram": float(macd_data["histogram"].iloc[-1]),
            },
            "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        }

        logger.info(f"Successfully calculated MACD for {ticker}")
        return JSONResponse(content=result)

    except TechnicalAnalysisError as e:
        logger.error(f"Error calculating MACD for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception:
        logger.exception(f"Unexpected error calculating MACD for {ticker}")
        raise HTTPException(status_code=500, detail="Internal server error")
