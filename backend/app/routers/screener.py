"""
Screener Router Module.

This module provides API endpoints for stock screening strategies,
including the 'Alpha Engine' module for identifying investment opportunities.
"""

from datetime import datetime
import logging

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from ..models.screener import ScreenerResponse, StockScreenerResult
from ..services.market_data import MarketDataProvider, MarketDataError


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
            "endpoint": "/screener/lynch-fast-growers",
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
            "endpoint": "/screener/value",
            "description": "Coming soon - Benjamin Graham value investing strategy",
            "status": "planned",
        },
        {
            "name": "Dividend Aristocrats",
            "endpoint": "/screener/dividend-aristocrats",
            "description": "Coming soon - High-quality dividend stocks",
            "status": "planned",
        },
        {
            "name": "Momentum Screener",
            "endpoint": "/screener/momentum",
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
