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
from ..financial_models.gann import get_gann_calculator
from ..services.yfinance_provider import YFinanceProvider

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


@router.get(
    "/{ticker}/gann",
    summary="Get Gann Square of 9 Levels",
    description="Calculate Gann Square of 9 support and resistance levels for a ticker.",
)
async def get_gann_levels(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol",
        min_length=1,
        max_length=10,
        pattern="^[A-Z]+$",
    ),
    reference_price: Optional[float] = Query(
        None,
        description="Reference price for calculations (default: 52-week low)",
        gt=0,
    ),
    num_levels: int = Query(
        5,
        description="Number of support/resistance levels to calculate",
        ge=1,
        le=10,
    ),
    tolerance: float = Query(
        0.02,
        description="Tolerance for key level detection as percentage (default: 0.02 = 2%)",
        ge=0.001,
        le=0.10,
    ),
    include_metadata: bool = Query(
        False,
        description="Include detailed metadata (angle, rotation, strength) for each level",
    ),
    allow_extreme_reference_price: bool = Query(
        False,
        description="Allow reference price >2x current price (default: false)",
    ),
):
    """
    Calculate Gann Square of 9 support and resistance levels.

    W.D. Gann's Square of 9 is a mathematical technique for identifying
    key support and resistance price levels based on angular relationships
    in a spiral pattern.

    **How it works:**
    - Uses a spiral starting at 1 in the center
    - Key angles (90°, 180°, 270°, 360°) represent important price levels
    - Calculates both support (below current price) and resistance (above)

    **Parameters:**
    - **ticker**: Stock ticker symbol
    - **reference_price**: Starting price for calculations (default: 52-week low)
    - **num_levels**: Number of levels to calculate (default: 5)
    - **tolerance**: Tolerance for key level detection as percentage (default: 0.02 = 2%).
      Determines how close the price must be to a level to be considered "at" that level.
      Range: 0.001 (0.1%) to 0.10 (10%)
    - **include_metadata**: Include detailed metadata for each level (angle, rotation, strength,
      distance from current price). When false (default), returns simple price lists.
    - **allow_extreme_reference_price**: Allow reference price >2x current price
      (default: false). Used for analyzing historical levels after major price drops.

    **Returns:**
    - Current price and reference price
    - List of support levels (below current price)
    - List of resistance levels (above current price)
    - Nearest support and resistance
    - Current position relative to levels

    **Example Request:**
    ```
    GET /technical/AAPL/gann
    GET /technical/NVDA/gann?num_levels=10
    GET /technical/TSLA/gann?reference_price=150.00
    GET /technical/GME/gann?reference_price=400.00&allow_extreme_reference_price=true
    ```

    **Example Response:**
    ```json
    {
      "ticker": "AAPL",
      "current_price": 185.50,
      "reference_price": 124.17,
      "support_levels": [180.25, 175.80, 170.45],
      "resistance_levels": [190.75, 195.20, 200.50],
      "nearest_support": 180.25,
      "nearest_resistance": 190.75,
      "current_position": "between_levels",
      "at_key_level": {
        "at_support": false,
        "at_resistance": false
      }
    }
    ```
    """
    try:
        logger.info(f"Received Gann Square of 9 request for {ticker}")

        # Initialize providers
        gann_calc = get_gann_calculator()
        yf_provider = YFinanceProvider()

        # Get current price and 52-week low
        fundamentals = yf_provider.get_fundamentals(ticker.upper())
        current_price = fundamentals.get("current_price")
        week_52_low = fundamentals.get("week_52_low")

        if not current_price:
            raise HTTPException(
                status_code=404,
                detail=f"Could not fetch current price for {ticker}"
            )

        # Validate and determine reference price
        if reference_price:
            # Validate user-provided reference price
            if reference_price <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Reference price must be positive"
                )
            if reference_price > current_price * 2:
                if not allow_extreme_reference_price:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Reference price ${reference_price:.2f} is more than 2x "
                            f"current price ${current_price:.2f}. This may indicate a data error "
                            f"or unusual market condition. If this is intentional, set "
                            f"allow_extreme_reference_price=true"
                        )
                    )
                logger.warning(
                    f"Using extreme reference price ${reference_price:.2f} "
                    f"(>2x current price ${current_price:.2f})"
                )
            ref_price = reference_price
        elif week_52_low:
            ref_price = week_52_low
            # Warn if current price is significantly above 52-week low
            if current_price > week_52_low * 1.5:
                pct_above = ((current_price / week_52_low - 1) * 100)
                logger.warning(
                    f"{ticker} is {pct_above:.0f}% above 52-week low "
                    f"(${current_price:.2f} vs ${week_52_low:.2f})"
                )
        else:
            # No reference price or 52-week data available
            raise HTTPException(
                status_code=400,
                detail=f"Cannot calculate Gann levels for {ticker}: "
                "No reference price provided and no 52-week data available. "
                "Please provide a reference_price parameter."
            )

        logger.info(
            f"Calculating Gann levels for {ticker}: "
            f"current={current_price:.2f}, reference={ref_price:.2f}, "
            f"metadata={include_metadata}"
        )

        # Calculate Gann levels (with or without metadata)
        if include_metadata:
            gann_levels = gann_calc.calculate_gann_levels_with_metadata(
                current_price=current_price,
                reference_price=ref_price,
                num_levels=num_levels,
                tolerance=tolerance,
            )
        else:
            gann_levels = gann_calc.calculate_gann_levels(
                current_price=current_price,
                reference_price=ref_price,
                num_levels=num_levels,
                tolerance=tolerance,
            )

        # Check if at key level
        key_level_check = gann_calc.is_at_key_level(
            current_price=current_price,
            reference_price=ref_price,
            tolerance=tolerance,
        )

        result = {
            "ticker": ticker.upper(),
            "current_price": current_price,
            "reference_price": ref_price,
            "week_52_low": week_52_low,
            "week_52_high": fundamentals.get("week_52_high"),
            "support_levels": gann_levels["support_levels"],
            "resistance_levels": gann_levels["resistance_levels"],
            "nearest_support": gann_levels["nearest_support"],
            "nearest_resistance": gann_levels["nearest_resistance"],
            "current_position": gann_levels["current_position"],
            "at_key_level": key_level_check,
            "num_levels_calculated": num_levels,
            "metadata_included": include_metadata,
        }

        logger.info(
            f"Successfully calculated Gann levels for {ticker}: "
            f"support={gann_levels['nearest_support']}, "
            f"resistance={gann_levels['nearest_resistance']}"
        )

        return JSONResponse(content=result)

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error calculating Gann levels for {ticker}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate Gann levels: {str(e)}"
        )
