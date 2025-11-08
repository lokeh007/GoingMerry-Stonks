"""
Screener Router Module.

This module provides API endpoints for stock screening strategies,
including the 'Alpha Engine' module for identifying investment opportunities.
"""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Body
from fastapi.responses import JSONResponse

from ..models.screener import (
    ScreenerResponse,
    StockScreenerResult,
    LynchCategory,
    FundamentalFilters,
    TechnicalFilters,
    AdvancedScreenerRequest,
    TechnicalIndicators,
    PatternDetection,
    GannLevels,
    RSICondition,
    MACDCondition,
    BulkowskiPattern,
    GannLocation,
    MarketRegime,
)
from ..services.market_data import MarketDataProvider, MarketDataError
from ..services.yfinance_provider import YFinanceProvider
from ..financial_models.gann import get_gann_calculator
from ..financial_models.patterns import get_pattern_detector


# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/screener",
    tags=["Alpha Engine - Stock Screener"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "/lynch-fast-growers",
    response_model=ScreenerResponse,
    summary="Lynch Fast Growers Screener",
    description="Screen for stocks using Peter Lynch's 'Fast Growers' investment strategy.",
)
async def get_lynch_fast_growers(
    min_earnings_growth: float = Query(
        15.0,
        description="Minimum earnings growth rate (%)",
        ge=0,
        le=1000,
    ),
    max_peg_ratio: float = Query(
        1.0,
        description="Maximum PEG ratio",
        ge=0,
        le=10,
    ),
    max_debt_to_equity: float = Query(
        0.5,
        description="Maximum debt-to-equity ratio",
        ge=0,
        le=10,
    ),
    max_earnings_growth: float = Query(
        30.0,
        description="Maximum earnings growth rate (%)",
        ge=0,
        le=1000,
    ),
    min_current_ratio: float = Query(
        1.0,
        description="Minimum current ratio (liquidity)",
        ge=0,
        le=10,
    ),
    min_market_cap: float = Query(
        1.0,
        description="Minimum market cap in billions",
        ge=0.1,
        le=10000,
    ),
    universe: str = Query(
        "popular",
        description="Stock universe to screen (popular, sp500_sample, tech)",
    ),
    limit: int = Query(
        20,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    ),
) -> ScreenerResponse:
    """
    Screen stocks using Peter Lynch's "Fast Growers" strategy.

    This screener identifies companies with strong growth potential based on
    the investment philosophy of Peter Lynch, legendary Fidelity fund manager.

    **Lynch Fast Growers Criteria:**

    1. **Strong Earnings Growth** (15-30% annually)
       - Companies growing faster than the market
       - Sustainable growth rates
       - Not too fast to be unsustainable

    2. **Excellent Valuation** (PEG ratio < 1.0)
       - PEG = PE Ratio / Earnings Growth Rate
       - Lynch's rule: PEG < 1.0 is excellent
       - Ensures not overpaying for growth

    3. **Financial Stability**
       - Current Ratio > 1.0 (can pay short-term debts)
       - Debt-to-Equity < 0.5 (low debt levels)
       - Strong balance sheet

    4. **Market Cap Filter**
       - Focus on mid-cap to large-cap stocks
       - More established companies with growth runway

    **Investment Philosophy:**
    Peter Lynch believed in "buying what you know" and finding companies with
    strong fundamentals trading at reasonable valuations. Fast growers are
    companies in early growth phase with 15-30% annual earnings growth.

    **Parameters:**
    - **min_earnings_growth**: Minimum annual earnings growth rate (default: 15%)
    - **max_earnings_growth**: Maximum annual earnings growth rate (default: 30%)
    - **max_peg_ratio**: Maximum acceptable PEG ratio (default: 1.0)
    - **max_debt_to_equity**: Maximum debt-to-equity ratio (default: 0.5)
    - **min_current_ratio**: Minimum current ratio (default: 1.0)
    - **min_market_cap**: Minimum market capitalization in billions (default: 1.0)
    - **universe**: Stock universe to screen (default: popular)
    - **limit**: Maximum number of stocks to return

    **Returns:**
    List of stocks that meet the Fast Growers criteria, ranked by score.

    **Example Request:**
    ```
    GET /screener/lynch-fast-growers?min_earnings_growth=15&max_peg_ratio=1.0
    ```

    **Example Response:**
    ```json
    {
        "screener_name": "Lynch Fast Growers",
        "description": "Peter Lynch's Fast Growers strategy",
        "total_results": 5,
        "results": [
            {
                "ticker": "NVDA",
                "company_name": "NVIDIA Corporation",
                "sector": "Technology",
                "price": 495.22,
                "pe_ratio": 65.3,
                "peg_ratio": 0.95,
                "earnings_growth": 25.2,
                "score": 92.5
            }
        ]
    }
    ```
    """
    try:
        logger.info(
            f"Lynch Fast Growers screening request: "
            f"eps_growth={min_earnings_growth}-{max_earnings_growth}%, "
            f"max_peg={max_peg_ratio}, max_d/e={max_debt_to_equity}"
        )

        # Build screening criteria
        criteria = {
            "min_earnings_growth": min_earnings_growth,
            "max_earnings_growth": max_earnings_growth,
            "max_peg_ratio": max_peg_ratio,
            "min_current_ratio": min_current_ratio,
            "max_debt_to_equity": max_debt_to_equity,
            "min_market_cap": min_market_cap,
            "universe": universe,
        }

        # Initialize market data provider
        market_data = MarketDataProvider()

        # Get stock universe to screen
        tickers = market_data.get_stock_universe(universe)
        logger.info(f"Screening {len(tickers)} stocks from '{universe}' universe")

        # Screen stocks
        results = []
        failed_tickers = []

        for ticker in tickers:
            try:
                # Fetch fundamental data
                financials = market_data.get_stock_financials(ticker)

                # Skip if essential data is missing
                if not financials.get("peg_ratio") or not financials.get("eps_growth"):
                    logger.debug(f"Skipping {ticker}: Missing PEG or EPS growth data")
                    continue

                # Apply screening criteria
                peg_ratio = financials["peg_ratio"] or float("inf")
                eps_growth = financials["eps_growth"] or 0
                debt_to_equity = financials["debt_to_equity"] or 0
                current_ratio = financials["current_ratio"] or 0
                market_cap = financials["market_cap"] or 0

                # Check all criteria
                passes_screen = (
                    min_earnings_growth <= eps_growth <= max_earnings_growth
                    and peg_ratio < max_peg_ratio
                    and debt_to_equity < max_debt_to_equity
                    and current_ratio >= min_current_ratio
                    and market_cap >= min_market_cap
                )

                if passes_screen:
                    # Get ticker details for company name and sector
                    try:
                        details = market_data.get_ticker_details(ticker)
                        company_name = details.get("name", ticker)
                        sector = details.get("sector", "")
                    except Exception:
                        company_name = ticker
                        sector = ""

                    # Calculate score (0-100)
                    score = _calculate_lynch_score(financials)

                    # Build reasons list
                    reasons = _generate_screening_reasons(financials, criteria)

                    # Create result object
                    result = StockScreenerResult(
                        ticker=ticker,
                        company_name=company_name,
                        sector=sector,
                        market_cap=market_cap,
                        price=financials.get("price"),
                        pe_ratio=financials.get("pe_ratio"),
                        peg_ratio=peg_ratio,
                        revenue_growth=financials.get("revenue_growth"),
                        earnings_growth=eps_growth,
                        debt_to_equity=debt_to_equity,
                        current_ratio=current_ratio,
                        score=score,
                        reasons=reasons,
                    )

                    results.append(result)
                    logger.info(f"✓ {ticker} passed screen (Score: {score:.1f})")

            except MarketDataError as e:
                logger.warning(f"Failed to fetch data for {ticker}: {e}")
                failed_tickers.append(ticker)
                continue
            except Exception as e:
                logger.error(f"Unexpected error screening {ticker}: {e}")
                failed_tickers.append(ticker)
                continue

        # Sort by score (highest first)
        results.sort(key=lambda x: x.score, reverse=True)

        # Limit results
        results = results[:limit]

        logger.info(
            f"Screening complete: {len(results)} stocks passed, "
            f"{len(failed_tickers)} failed/skipped"
        )

        response = ScreenerResponse(
            screener_name="Lynch Fast Growers",
            description=(
                f"Peter Lynch's Fast Growers strategy: PEG < {max_peg_ratio}, "
                f"EPS Growth {min_earnings_growth}-{max_earnings_growth}%, "
                f"D/E < {max_debt_to_equity}"
            ),
            total_results=len(results),
            results=results,
            timestamp=datetime.now(),
            criteria=criteria,
        )

        return response

    except Exception as e:
        logger.exception("Error in Lynch Fast Growers screening")
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")


@router.get(
    "/screeners",
    summary="List Available Screeners",
    description="Get a list of all available screening strategies.",
)
async def list_screeners():
    """
    List all available stock screening strategies.

    Returns information about each screener including its criteria and
    typical use cases.

    **Returns:**
    List of available screeners with descriptions.
    """
    screeners = [
        {
            "name": "Lynch Fast Growers",
            "endpoint": "/api/screener/lynch-fast-growers",
            "description": "Peter Lynch's strategy for finding fast-growing companies",
            "criteria": [
                "Earnings growth: 10-25% annually",
                "PEG ratio < 2.5",
                "Current ratio > 1.0",
                "Debt-to-equity < 2.0",
            ],
            "ideal_for": "Growth investors seeking undervalued high-growth stocks",
            "risk_level": "Medium",
            "typical_holding_period": "2-5 years",
        },
        {
            "name": "Value Screener",
            "endpoint": "/api/screener/value",
            "description": "Coming soon - Benjamin Graham value investing strategy",
            "status": "planned",
        },
        {
            "name": "Dividend Aristocrats",
            "endpoint": "/api/screener/dividend-aristocrats",
            "description": "Coming soon - High-quality dividend stocks",
            "status": "planned",
        },
        {
            "name": "Momentum Screener",
            "endpoint": "/api/screener/momentum",
            "description": "Coming soon - Stocks with strong price momentum",
            "status": "planned",
        },
    ]

    return JSONResponse(
        content={
            "total_screeners": len(screeners),
            "screeners": screeners,
            "alpha_engine_version": "1.0.0",
        }
    )


@router.get(
    "/presets/{category}",
    summary="Get Lynch Category Filter Presets",
    description="Get recommended filter values for a specific Peter Lynch stock category.",
)
async def get_category_presets(category: LynchCategory):
    """
    Get recommended filter presets for a Lynch stock category.

    Each category has specific criteria based on Peter Lynch's investment philosophy:
    - **Fast Growers**: Rapid growth at reasonable prices
    - **Stalwarts**: Large, reliable companies on sale
    - **Slow Growers**: High dividend, stable companies
    - **Cyclicals**: Timing business cycles
    - **Turnarounds**: Companies recovering from difficulties
    - **Asset Plays**: Hidden value in assets

    **Parameters:**
    - **category**: Lynch category (fast_growers, stalwarts, etc.)

    **Returns:**
    Recommended filter values and investment philosophy for the category.
    """
    presets = {
        LynchCategory.FAST_GROWERS: {
            "category": "fast_growers",
            "name": "Fast Growers",
            "description": "Companies with 15-30% annual growth, trading at reasonable valuations",
            "philosophy": "Lynch's most profitable category. Look for companies in early growth phase with strong fundamentals and PEG < 1.0",
            "filters": {
                "max_peg_ratio": 1.0,
                "min_eps_growth": 15.0,
                "max_eps_growth": 30.0,
                "max_debt_to_equity": 0.6,
                "min_roe": 15.0,
                "max_institutional_ownership": 30.0,
                "min_market_cap": 1.0,
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Growth investors seeking 'tenbagger' potential",
            "holding_period": "2-5 years",
            "risk_level": "Medium",
        },
        LynchCategory.STALWARTS: {
            "category": "stalwarts",
            "name": "Stalwarts",
            "description": "Large, well-known companies with consistent moderate growth",
            "philosophy": "Blue-chip stocks bought during market corrections. Less exciting but reliable 30-50% gains",
            "filters": {
                "max_peg_ratio": 1.5,
                "min_eps_growth": 10.0,
                "max_eps_growth": 15.0,
                "max_debt_to_equity": 0.8,
                "min_roe": 12.0,
                "max_institutional_ownership": None,  # Any
                "min_market_cap": 10.0,  # Large caps
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Conservative investors seeking reliability",
            "holding_period": "3-5 years",
            "risk_level": "Low",
        },
        LynchCategory.SLOW_GROWERS: {
            "category": "slow_growers",
            "name": "Slow Growers",
            "description": "Mature companies with high dividends and minimal growth",
            "philosophy": "Buy for dividends, not price appreciation. Utilities, mature industrials",
            "filters": {
                "max_peg_ratio": None,  # Not applicable
                "min_eps_growth": None,  # Can be negative
                "max_eps_growth": 10.0,
                "max_debt_to_equity": 1.0,
                "min_roe": 8.0,
                "max_institutional_ownership": None,
                "min_market_cap": 5.0,
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Income investors seeking stable dividends",
            "holding_period": "5+ years",
            "risk_level": "Very Low",
        },
        LynchCategory.CYCLICALS: {
            "category": "cyclicals",
            "name": "Cyclicals",
            "description": "Companies whose fortunes rise and fall with economic cycles",
            "philosophy": "Timing is everything. Buy at cycle bottom, sell at peak. Airlines, autos, steel",
            "filters": {
                "max_peg_ratio": 1.0,
                "min_eps_growth": None,  # Cyclical, not linear
                "max_eps_growth": None,
                "max_debt_to_equity": 1.0,
                "min_roe": None,  # Can be negative during downturns
                "max_institutional_ownership": None,
                "min_market_cap": 1.0,
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Experienced investors who can time economic cycles",
            "holding_period": "6 months - 2 years",
            "risk_level": "High",
        },
        LynchCategory.TURNAROUNDS: {
            "category": "turnarounds",
            "name": "Turnarounds",
            "description": "Companies recovering from severe difficulties",
            "philosophy": "High risk, high reward. Focus on balance sheet health and signs of recovery",
            "filters": {
                "max_peg_ratio": None,  # Often negative earnings
                "min_eps_growth": None,  # Can be negative
                "max_eps_growth": None,
                "max_debt_to_equity": 0.5,  # Must have manageable debt
                "min_roe": None,  # Can be negative
                "max_institutional_ownership": None,
                "min_market_cap": 0.5,
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Risk-tolerant investors seeking asymmetric upside",
            "holding_period": "1-3 years",
            "risk_level": "Very High",
        },
        LynchCategory.ASSET_PLAYS: {
            "category": "asset_plays",
            "name": "Asset Plays",
            "description": "Companies with hidden assets undervalued by the market",
            "philosophy": "Market doesn't recognize true value of assets (real estate, patents, inventory)",
            "filters": {
                "max_peg_ratio": None,  # Not applicable
                "min_eps_growth": None,
                "max_eps_growth": None,
                "max_debt_to_equity": 0.5,  # Must be able to hold assets
                "min_roe": None,
                "max_institutional_ownership": 50.0,  # Often undiscovered
                "min_market_cap": 0.3,  # Often small caps
                "min_current_ratio": 1.0,
            },
            "ideal_for": "Value investors seeking hidden gems",
            "holding_period": "2-5 years",
            "risk_level": "Medium-High",
        },
    }

    preset = presets.get(category)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    logger.info(f"Returning preset for category: {category}")
    return JSONResponse(content=preset)


@router.get(
    "/vix",
    summary="Get Market Volatility (VIX) Data",
    description="Get current VIX value and market regime classification.",
)
async def get_vix_data():
    """
    Get current VIX (Volatility Index) and market regime.

    The VIX, known as the "Fear Gauge", measures market volatility expectations.

    **Market Regimes:**
    - **Low Fear** (VIX < 20): Bullish, low volatility market
    - **Moderate Fear** (VIX 20-30): Normal market conditions
    - **High Fear** (VIX > 30): Bearish, high volatility market (opportunities for deep value)

    **Returns:**
    VIX value, market regime, and timestamp.
    """
    try:
        yf_provider = YFinanceProvider()
        vix_info = yf_provider.get_vix_data()

        logger.info(
            f"VIX data retrieved: {vix_info['value']:.2f} ({vix_info['regime_label']})"
        )

        return JSONResponse(content=vix_info)

    except Exception as e:
        logger.error(f"Error fetching VIX data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch VIX data: {str(e)}")


@router.post(
    "/advanced",
    response_model=ScreenerResponse,
    summary="Advanced Multi-Layered Stock Screener",
    description="Screen stocks using Lynch fundamentals, technical triggers, and market context.",
)
async def advanced_screener(request: AdvancedScreenerRequest = Body(...)):
    """
    Run advanced multi-layered stock screening.

    This endpoint combines:
    1. **Lynch Fundamentals** (Section 1): Filter by PEG, EPS growth, D/E, ROE, etc.
    2. **Technical Triggers** (Section 2): Filter by RSI, MACD, patterns, Gann levels
    3. **Market Context** (Section 3): Filter by VIX-based market regime

    **Example Classic Setup:**
    ```json
    {
        "lynch_category": "fast_growers",
        "fundamental_filters": {
            "max_peg_ratio": 1.0,
            "min_eps_growth": 15,
            "max_eps_growth": 30,
            "max_debt_to_equity": 0.6
        },
        "technical_filters": {
            "rsi_condition": "oversold",
            "macd_condition": "bullish_crossover"
        },
        "market_regime": "high_fear"
    }
    ```

    This finds high-quality fast growers that are oversold during market panic - a classic professional setup.

    **Returns:**
    Paginated list of stocks with full fundamental and technical data.
    """
    try:
        logger.info(
            f"Advanced screening request: category={request.lynch_category.value}, "
            f"universe={request.universe}, page={request.page}"
        )

        # Initialize providers
        market_data = MarketDataProvider()
        yf_provider = YFinanceProvider()
        gann_calc = get_gann_calculator()
        pattern_detector = get_pattern_detector()

        # Get stock universe
        if request.universe in ["nasdaq", "nyse", "all"]:
            tickers = yf_provider.get_stock_universe(request.universe.upper())
        else:
            tickers = market_data.get_stock_universe(request.universe)

        logger.info(f"Screening {len(tickers)} stocks from '{request.universe}' universe")

        # Phase 1: Apply fundamental filters (Lynch criteria)
        fundamental_passed = []
        for ticker in tickers:
            try:
                financials = market_data.get_stock_financials(ticker)

                if not financials.get("peg_ratio") or not financials.get("eps_growth"):
                    continue

                # Apply fundamental filters
                if not _passes_fundamental_filters(financials, request.fundamental_filters):
                    continue

                fundamental_passed.append((ticker, financials))

            except Exception as e:
                logger.debug(f"Skipping {ticker}: {e}")
                continue

        logger.info(f"Phase 1 complete: {len(fundamental_passed)} passed fundamental filters")

        # Phase 2 & 3: Apply technical filters and market regime
        results = []
        apply_technical = _should_apply_technical_filters(request.technical_filters)
        apply_market_regime = request.market_regime != MarketRegime.ANY

        # Get VIX if needed
        current_vix = None
        if apply_market_regime:
            try:
                vix_data = yf_provider.get_vix_data()
                current_vix = vix_data["value"]
                current_regime = vix_data["regime"]

                # Filter by market regime
                if not _passes_market_regime_filter(current_vix, current_regime, request.market_regime):
                    logger.info(
                        f"Market regime filter failed: current={current_regime}, "
                        f"required={request.market_regime.value}"
                    )
                    # Return empty results if market regime doesn't match
                    return ScreenerResponse(
                        screener_name=f"Advanced Screener - {request.lynch_category.value}",
                        description=f"Market regime {current_regime} does not match filter {request.market_regime.value}",
                        total_results=0,
                        results=[],
                        timestamp=datetime.now(),
                        criteria=request.model_dump(),
                    )
            except Exception as e:
                logger.warning(f"Could not fetch VIX, skipping market regime filter: {e}")

        # Process each stock that passed fundamentals
        for ticker, financials in fundamental_passed:
            try:
                # Fetch technical data if needed
                tech_indicators = None
                pattern = None
                gann = None

                if apply_technical:
                    try:
                        # Get technical indicators
                        indicators = yf_provider.get_technical_indicators(ticker, period="3mo")

                        # Apply RSI filter
                        if request.technical_filters.rsi_condition != RSICondition.ANY:
                            if not _passes_rsi_filter(indicators, request.technical_filters.rsi_condition):
                                continue

                        # Apply MACD filter
                        if request.technical_filters.macd_condition != MACDCondition.ANY:
                            if not _passes_macd_filter(indicators, request.technical_filters.macd_condition):
                                continue

                        # Build technical indicators model
                        tech_indicators = TechnicalIndicators(
                            rsi_current=indicators["rsi"]["current"],
                            rsi_oversold=indicators["rsi"]["oversold"],
                            rsi_overbought=indicators["rsi"]["overbought"],
                            macd_bullish_crossover=indicators["macd"]["bullish_crossover"],
                            macd_bearish_crossover=indicators["macd"]["bearish_crossover"],
                        )

                        # Pattern detection
                        if request.technical_filters.pattern != BulkowskiPattern.ANY:
                            hist_data = yf_provider.get_historical_data(ticker, period="6mo")

                            if request.technical_filters.pattern == BulkowskiPattern.PIPE_BOTTOM:
                                pattern_result = pattern_detector.detect_pipe_bottom(hist_data)
                            elif request.technical_filters.pattern == BulkowskiPattern.DOUBLE_BOTTOM:
                                pattern_result = pattern_detector.detect_double_bottom(hist_data)
                            else:
                                pattern_result = {"detected": False}

                            if not pattern_result["detected"]:
                                continue

                            pattern = PatternDetection(**pattern_result)

                        # Gann level detection
                        if request.technical_filters.gann_location != GannLocation.ANY:
                            current_price = financials.get("price", 0)
                            if current_price:
                                gann_levels = gann_calc.calculate_gann_levels(current_price)
                                at_level = gann_calc.is_at_key_level(current_price, current_price)

                                if request.technical_filters.gann_location == GannLocation.AT_SUPPORT:
                                    if not at_level["at_support"]:
                                        continue
                                elif request.technical_filters.gann_location == GannLocation.AT_RESISTANCE:
                                    if not at_level["at_resistance"]:
                                        continue

                                gann = GannLevels(
                                    nearest_support=gann_levels["nearest_support"],
                                    nearest_resistance=gann_levels["nearest_resistance"],
                                    at_support=at_level["at_support"],
                                    at_resistance=at_level["at_resistance"],
                                    position=gann_levels["current_position"],
                                )

                    except Exception as e:
                        logger.debug(f"Technical analysis failed for {ticker}: {e}")
                        continue

                # Get ticker details
                try:
                    details = market_data.get_ticker_details(ticker)
                    company_name = details.get("name", ticker)
                    sector = details.get("sector", "")
                except Exception:
                    company_name = ticker
                    sector = ""

                # Calculate score
                score = _calculate_lynch_score(financials)

                # Generate reasons
                # Map model dump keys to expected keys for _generate_screening_reasons
                _criteria_key_map = {
                    "min_eps_growth": "min_earnings_growth",
                    "max_eps_growth": "max_earnings_growth",
                    "min_peg_ratio": "min_peg_ratio",
                    "max_peg_ratio": "max_peg_ratio",
                    "min_pe_ratio": "min_pe_ratio",
                    "max_pe_ratio": "max_pe_ratio",
                    "min_revenue_growth": "min_revenue_growth",
                    "max_revenue_growth": "max_revenue_growth",
                    "min_debt_to_equity": "min_debt_to_equity",
                    "max_debt_to_equity": "max_debt_to_equity",
                    "min_current_ratio": "min_current_ratio",
                    "max_current_ratio": "max_current_ratio",
                    "min_roe": "min_roe",
                    "max_roe": "max_roe",
                    "min_institutional_ownership": "min_institutional_ownership",
                    "max_institutional_ownership": "max_institutional_ownership",
                }
                raw_criteria = request.fundamental_filters.model_dump()
                criteria = {}
                for k, v in raw_criteria.items():
                    mapped_key = _criteria_key_map.get(k, k)
                    criteria[mapped_key] = v
                reasons = _generate_screening_reasons(financials, criteria)

                # Create result
                result = StockScreenerResult(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    market_cap=financials.get("market_cap"),
                    price=financials.get("price"),
                    pe_ratio=financials.get("pe_ratio"),
                    peg_ratio=financials.get("peg_ratio"),
                    revenue_growth=financials.get("revenue_growth"),
                    earnings_growth=financials.get("eps_growth"),
                    debt_to_equity=financials.get("debt_to_equity"),
                    current_ratio=financials.get("current_ratio"),
                    roe=financials.get("roe"),
                    institutional_ownership=financials.get("institutional_ownership"),
                    technical_indicators=tech_indicators,
                    pattern=pattern,
                    gann_levels=gann,
                    score=score,
                    reasons=reasons,
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                continue

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Apply pagination
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_results = results[start_idx:end_idx]

        logger.info(
            f"Screening complete: {len(results)} total, "
            f"returning {len(paginated_results)} for page {request.page}"
        )

        return ScreenerResponse(
            screener_name=f"Advanced Screener - {request.lynch_category.value.replace('_', ' ').title()}",
            description=f"Multi-layered screening with fundamental and technical filters",
            total_results=len(results),
            results=paginated_results,
            timestamp=datetime.now(),
            criteria=request.model_dump(),
        )

    except Exception as e:
        logger.exception("Error in advanced screening")
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")


# Helper functions for advanced screener

def _passes_fundamental_filters(financials: dict, filters: FundamentalFilters) -> bool:
    """Check if stock passes fundamental filters."""
    # PEG Ratio
    if filters.max_peg_ratio is not None:
        peg = financials.get("peg_ratio", float("inf"))
        if peg > filters.max_peg_ratio:
            return False

    # EPS Growth
    eps_growth = financials.get("eps_growth", 0)
    if filters.min_eps_growth is not None and eps_growth < filters.min_eps_growth:
        return False
    if filters.max_eps_growth is not None and eps_growth > filters.max_eps_growth:
        return False

    # Debt-to-Equity
    if filters.max_debt_to_equity is not None:
        de_ratio = financials.get("debt_to_equity", float("inf"))
        if de_ratio > filters.max_debt_to_equity:
            return False

    # ROE
    if filters.min_roe is not None:
        roe = financials.get("roe", 0)
        if roe < filters.min_roe:
            return False

    # Institutional Ownership
    if filters.max_institutional_ownership is not None:
        inst_own = financials.get("institutional_ownership", 100)
        if inst_own > filters.max_institutional_ownership:
            return False

    # Market Cap
    if filters.min_market_cap is not None:
        market_cap = financials.get("market_cap", 0)
        if market_cap < filters.min_market_cap:
            return False

    # Current Ratio
    if filters.min_current_ratio is not None:
        current_ratio = financials.get("current_ratio", 0)
        if current_ratio < filters.min_current_ratio:
            return False

    return True


def _should_apply_technical_filters(filters: TechnicalFilters) -> bool:
    """Check if any technical filters are active."""
    return (
        filters.rsi_condition != RSICondition.ANY
        or filters.macd_condition != MACDCondition.ANY
        or filters.pattern != BulkowskiPattern.ANY
        or filters.gann_location != GannLocation.ANY
    )


def _passes_rsi_filter(indicators: dict, condition: RSICondition) -> bool:
    """Check if RSI passes filter condition."""
    rsi = indicators["rsi"]["current"]
    if rsi is None:
        return False

    if condition == RSICondition.OVERSOLD:
        return rsi < 30
    elif condition == RSICondition.NEUTRAL:
        return 30 <= rsi <= 70
    elif condition == RSICondition.OVERBOUGHT:
        return rsi > 70

    return True


def _passes_macd_filter(indicators: dict, condition: MACDCondition) -> bool:
    """Check if MACD passes filter condition."""
    if condition == MACDCondition.BULLISH_CROSSOVER:
        return indicators["macd"]["bullish_crossover"]
    elif condition == MACDCondition.BEARISH_CROSSOVER:
        return indicators["macd"]["bearish_crossover"]

    return True


def _passes_market_regime_filter(vix: float, current_regime: str, required_regime: MarketRegime) -> bool:
    """Check if current market regime matches required regime."""
    if required_regime == MarketRegime.ANY:
        return True
    elif required_regime == MarketRegime.LOW_FEAR:
        return current_regime == "low_fear"
    elif required_regime == MarketRegime.MODERATE_FEAR:
        return current_regime == "moderate_fear"
    elif required_regime == MarketRegime.HIGH_FEAR:
        return current_regime == "high_fear"

    return True


def _calculate_lynch_score(financials: dict) -> float:
    """
    Calculate a Lynch Fast Growers score for a stock.

    The score is calculated based on:
    - PEG Ratio (40 points): Lower is better
    - EPS Growth (30 points): Higher is better (within 15-30% range)
    - Debt-to-Equity (20 points): Lower is better
    - Current Ratio (10 points): Higher is better

    Args:
        financials: Dict containing financial metrics

    Returns:
        Score from 0-100 (higher is better)
    """
    score = 0.0

    # PEG Ratio score (40 points max)
    # Perfect score: PEG < 0.5, Good: 0.5-0.75, Acceptable: 0.75-1.0
    peg = financials.get("peg_ratio", float("inf"))
    if peg <= 0.5:
        score += 40
    elif peg <= 0.75:
        score += 30
    elif peg <= 1.0:
        score += 20
    elif peg <= 1.5:
        score += 10

    # EPS Growth score (30 points max)
    # Perfect: 20-25%, Good: 15-20% or 25-30%, Lower gets fewer points
    eps_growth = financials.get("eps_growth", 0)
    if 20 <= eps_growth <= 25:
        score += 30
    elif 15 <= eps_growth < 20:
        score += 25
    elif 25 < eps_growth <= 30:
        score += 25
    elif 10 <= eps_growth < 15:
        score += 15
    elif eps_growth > 30:
        # Too high growth may be unsustainable
        score += 10

    # Debt-to-Equity score (20 points max)
    # Perfect: D/E < 0.25, Good: 0.25-0.5, Acceptable: 0.5-1.0
    de_ratio = financials.get("debt_to_equity", float("inf"))
    if de_ratio < 0.25:
        score += 20
    elif de_ratio < 0.5:
        score += 15
    elif de_ratio < 1.0:
        score += 10
    elif de_ratio < 1.5:
        score += 5

    # Current Ratio score (10 points max)
    # Perfect: > 2.5, Good: 2.0-2.5, Acceptable: 1.5-2.0, Minimum: 1.0-1.5
    current_ratio = financials.get("current_ratio", 0)
    if current_ratio >= 2.5:
        score += 10
    elif current_ratio >= 2.0:
        score += 8
    elif current_ratio >= 1.5:
        score += 6
    elif current_ratio >= 1.0:
        score += 4

    return round(score, 1)


def _generate_screening_reasons(financials: dict, criteria: dict) -> list[str]:
    """
    Generate human-readable reasons why a stock passed screening.

    Args:
        financials: Dict containing financial metrics
        criteria: Dict containing screening criteria

    Returns:
        List of reason strings
    """
    reasons = []

    # PEG Ratio reason
    peg = financials.get("peg_ratio", 0)
    if peg:
        if peg < 0.5:
            reasons.append(
                f"Excellent PEG ratio ({peg:.2f}) - significantly undervalued"
            )
        elif peg < 0.75:
            reasons.append(f"Great PEG ratio ({peg:.2f}) - good value")
        elif peg < 1.0:
            reasons.append(f"Good PEG ratio ({peg:.2f}) - fairly valued")

    # EPS Growth reason
    eps_growth = financials.get("eps_growth", 0)
    if eps_growth:
        if eps_growth >= 25:
            reasons.append(f"Strong EPS growth ({eps_growth:.1f}%)")
        elif eps_growth >= 20:
            reasons.append(f"Solid EPS growth ({eps_growth:.1f}%)")
        elif eps_growth >= 15:
            reasons.append(f"Healthy EPS growth ({eps_growth:.1f}%)")

    # Debt-to-Equity reason
    de_ratio = financials.get("debt_to_equity", 0)
    if de_ratio is not None:
        if de_ratio < 0.25:
            reasons.append(f"Minimal debt (D/E: {de_ratio:.2f})")
        elif de_ratio < 0.5:
            reasons.append(f"Low debt levels (D/E: {de_ratio:.2f})")

    # Current Ratio reason
    current_ratio = financials.get("current_ratio", 0)
    if current_ratio:
        if current_ratio >= 2.5:
            reasons.append(f"Excellent liquidity (CR: {current_ratio:.2f})")
        elif current_ratio >= 2.0:
            reasons.append(f"Strong liquidity (CR: {current_ratio:.2f})")
        elif current_ratio >= 1.5:
            reasons.append(f"Good liquidity (CR: {current_ratio:.2f})")

    # Revenue Growth reason
    revenue_growth = financials.get("revenue_growth", 0)
    if revenue_growth and revenue_growth >= 15:
        reasons.append(f"Strong revenue growth ({revenue_growth:.1f}%)")

    # If we have very few reasons, add at least one generic one
    if len(reasons) < 2:
        reasons.append("Meets Lynch Fast Growers criteria")

    return reasons
