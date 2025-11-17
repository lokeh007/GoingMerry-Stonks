#!/usr/bin/env python3
"""
Regular Stock Screeners - Cloud Run Job (Batched Execution)

Runs The Undiscovered and The Coiled Spring screeners against the full NYSE + NASDAQ
universe (~6000 stocks) in 5 batches to respect yfinance rate limits.

NOTE: Smart Money (options flow) screener runs separately in run_smart_money_screener.py
      due to higher API token consumption (45 req/min vs 60 req/min).

Batch Schedule:
- Batch 1: 4:30 PM ET - Tickers A-D (~1200 stocks)
- Batch 2: 6:00 PM ET - Tickers E-J (~1200 stocks)
- Batch 3: 7:30 PM ET - Tickers K-N (~1200 stocks)
- Batch 4: 9:00 PM ET - Tickers O-S (~1200 stocks)
- Batch 5: 10:30 PM ET - Tickers T-Z (~1200 stocks)

Estimated runtime per batch: ~90 minutes
Rate limit: 60 requests/minute
Data sources: Yahoo Finance (free, no API keys required)
"""

import os
import sys
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore
from app.services.yfinance_provider import YFinanceProvider
from app.services.ticker_universe import TickerUniverseProvider
from app.services.delisted_ticker_cache import DelistedTickerCache
from app.utils.firestore import convert_numpy_types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Suppress404Filter(logging.Filter):
    """Custom filter to suppress 404 errors from yfinance while preserving other errors."""

    # Compile regex once at class level for performance
    _404_PATTERN = re.compile(r'\b404\b')

    def filter(self, record):
        """
        Return False for 404-related messages to filter them out, True otherwise.

        Uses word boundary matching for '404' to avoid false positives
        (e.g., "4040" in timeout messages).
        """
        msg = record.getMessage().lower()
        return not (self._404_PATTERN.search(msg) or "not found" in msg)


# Suppress yfinance ERROR logging for 404s only (preserves real errors)
yf_logger = logging.getLogger('yfinance')
yf_logger.addFilter(Suppress404Filter())


class DailyScreenerJob:
    """Orchestrates daily screener execution and Firestore storage."""

    # Compile regex once at class level for performance
    _404_PATTERN = re.compile(r'\b404\b')

    def __init__(self, batch_number: Optional[int] = None):
        """
        Initialize Firestore client and yfinance provider.

        Args:
            batch_number: Batch number (1, 2, or 3) for staggered execution.
                         If None, uses representative universe (legacy mode).
        """
        self.db = firestore.Client()
        # YFinanceProvider with optimized rate limit (58 req/min, 97% of 60 limit)
        self.yf_provider = YFinanceProvider(max_requests_per_minute=58)
        self.ticker_provider = TickerUniverseProvider()
        self.delisted_cache = DelistedTickerCache(ttl_days=30)  # Retry delisted after 30 days
        self.run_timestamp = datetime.now(timezone.utc)
        self.batch_number = batch_number

        # Metrics tracking
        self.metrics = {
            'api_calls': 0,
            'start_time': None
        }

        if batch_number:
            logger.info(f"Initializing Daily Screener Job - Batch {batch_number}/5")
            logger.info("Rate limiting: 58 req/min with adaptive exponential backoff")

    def _categorize_error(
        self,
        ticker: str,
        error: Exception,
        failed_tickers: List[str],
        not_found_tickers: List[str]
    ) -> None:
        """
        Categorize ticker errors as 404s or real failures.

        Args:
            ticker: Stock ticker symbol
            error: Exception that was raised
            failed_tickers: List to append real failures to
            not_found_tickers: List to append 404s to
        """
        error_msg = str(error).lower()

        is_404 = (
            self._404_PATTERN.search(error_msg) or
            'not found' in error_msg or
            'no data' in error_msg or
            'no fundamentals' in error_msg
        )

        # Check if it's a rate limit or timeout error
        is_rate_limit = 'rate limit' in error_msg or 'too many requests' in error_msg
        is_timeout = 'timeout' in error_msg or 'timed out' in error_msg

        if is_404:
            # Expected - ticker doesn't exist or no data available
            not_found_tickers.append(ticker)
        else:
            # Unexpected error - log for debugging with specific error type
            if is_rate_limit:
                logger.warning(f"Rate limit error for {ticker}: {error}")
            elif is_timeout:
                logger.warning(f"Timeout error for {ticker}: {error}")
            else:
                logger.warning(f"Unexpected error screening {ticker}: {error}")
            failed_tickers.append(ticker)

    def _log_progress(self, current: int, total: int, start_time: datetime) -> None:
        """
        Log screening progress with ETA calculation.

        Args:
            current: Current ticker number being processed
            total: Total number of tickers to process
            start_time: Start time of screening operation
        """
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = current / elapsed if elapsed > 0 else 0
        remaining = total - current
        eta_seconds = remaining / rate if rate > 0 else 0
        logger.info(
            f"Progress: {current}/{total} ({current/total*100:.1f}%) | "
            f"Rate: {rate:.2f} tickers/sec | "
            f"ETA: {eta_seconds/60:.1f} min"
        )

    def get_full_exchange_universe(self) -> List[str]:
        """
        Get full NYSE + NASDAQ stock universe with basic filters.

        If batch_number is set, returns stocks for that specific batch.
        Otherwise, returns representative universe for backward compatibility.

        Filters (applied by TickerUniverseProvider):
        - Market cap >= $100M (exclude penny stocks)
        - Average volume > 100K shares/day (exclude illiquid)
        - Price >= $2 (exclude sub-$2 stocks)
        - Remove warrants, preferred stocks, indexes

        Returns:
            List of ticker symbols:
            - Batch mode: ~1200 stocks per batch
            - Legacy mode: ~109 representative stocks
        """
        if self.batch_number:
            # Batched execution: Get stocks for this specific batch
            logger.info(f"Fetching batch {self.batch_number}/5 from full NYSE + NASDAQ universe...")
            universe = self.ticker_provider.get_batch_universe(self.batch_number)
            logger.info(
                f"Batch {self.batch_number}: {len(universe)} stocks "
                f"(Range: {universe[0]} to {universe[-1]})"
            )
        else:
            # Legacy mode: Use representative universe for testing
            logger.info("Fetching representative universe (legacy mode)...")
            universe = self._get_representative_universe()
            logger.info(f"Representative universe: {len(universe)} stocks")

        return universe

    def _get_representative_universe(self) -> List[str]:
        """
        Get representative universe for testing (500 stocks).

        In production, replace with full NYSE/NASDAQ API call.
        """
        # Start with existing universes
        popular = self.yf_provider.get_stock_universe("popular")
        sp500_sample = self.yf_provider.get_stock_universe("sp500_sample")
        tech = self.yf_provider.get_stock_universe("tech")

        # Add crypto/mining stocks (for Asset Plays)
        crypto_stocks = [
            "MSTR", "MARA", "RIOT", "HUT", "CLSK", "BITF", "CIFR", "CORZ",
            "BTBT", "GLXY", "COIN", "HOOD", "SQ"
        ]

        # Add gold miners
        gold_stocks = [
            "NEM", "GOLD", "AEM", "FNV", "WPM", "KGC", "AU", "GFI", "KL", "RGLD"
        ]

        # Add high-growth small caps (typical Undiscovered targets)
        small_caps = [
            "PLTR", "SNOW", "CRWD", "NET", "DDOG", "ZS", "OKTA", "TEAM",
            "FTNT", "PANW", "DOCU", "TWLO", "MDB", "ESTC"
        ]

        # Add volatile stocks (Coiled Spring candidates)
        volatile_stocks = [
            "AMC", "GME", "BBBY", "BYND", "PLUG", "FCEL", "BLNK", "CHPT"
        ]

        # Combine and deduplicate
        universe = list(set(
            popular + sp500_sample + tech +
            crypto_stocks + gold_stocks +
            small_caps + volatile_stocks
        ))

        logger.info(f"Representative universe: {len(universe)} stocks (MVP mode)")
        logger.warning("Production deployment should use full NYSE/NASDAQ API")

        return universe

    def _passes_basic_filters(
        self,
        ticker: str,
        fundamentals: Dict[str, Any]
    ) -> bool:
        """
        Check if ticker passes basic quality filters before fetching additional data.

        This is a LAZY LOADING optimization - we only fetch analyst/volatility data
        if the ticker passes these preliminary filters, saving ~47% of API calls.

        Args:
            ticker: Stock ticker symbol
            fundamentals: Basic fundamental data

        Returns:
            True if ticker should be evaluated further, False to skip
        """
        # Filter 1: Market cap check (avoid micro-caps)
        market_cap = fundamentals.get("market_cap", 0)
        if market_cap < 100_000_000:  # < $100M
            logger.debug(f"{ticker}: Market cap too low (${market_cap:,.0f}), skipping")
            return False

        # Filter 2: Price check (avoid penny stocks)
        current_price = fundamentals.get("current_price", 0)
        if current_price is None or current_price < 2:
            logger.debug(f"{ticker}: Price too low (${current_price}), skipping")
            return False

        # Filter 3: Has valid sector (avoid incomplete data)
        sector = fundamentals.get("sector")
        if not sector or sector == "Unknown":
            logger.debug(f"{ticker}: No sector data, skipping")
            return False

        return True

    def _should_evaluate_undiscovered(
        self,
        fundamentals: Dict[str, Any],
        params: Dict[str, Any]
    ) -> bool:
        """
        Check if ticker is worth evaluating for Undiscovered screener.

        This avoids fetching analyst data for tickers that clearly won't pass.

        Args:
            fundamentals: Basic fundamental data
            params: Screener parameters

        Returns:
            True if should fetch analyst data, False to skip
        """
        # Check if institutional ownership data exists
        inst_ownership = fundamentals.get("institutional_ownership")
        if inst_ownership is None:
            logger.debug(f"No institutional ownership data, skipping Undiscovered")
            return False

        # Early exit if institutional ownership way too high
        max_institutional_ownership = params["max_institutional_ownership"]
        if inst_ownership > (max_institutional_ownership * 2):
            logger.debug(f"Inst. ownership {inst_ownership}% >> {max_institutional_ownership}%, skipping Undiscovered")
            return False

        return True

    def _should_evaluate_coiled_spring(
        self,
        fundamentals: Dict[str, Any]
    ) -> bool:
        """
        Check if ticker is worth evaluating for Coiled Spring screener.

        This avoids fetching volatility data for tickers that clearly won't pass.

        Args:
            fundamentals: Basic fundamental data

        Returns:
            True if should fetch volatility data, False to skip
        """
        # For now, always evaluate Coiled Spring if fundamentals look good
        # Can add more filters here based on price action, volume, etc.
        return True

    def _process_ticker(
        self,
        ticker: str,
        undiscovered_params: Dict[str, Any],
        coiled_spring_params: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]:
        """
        Process a single ticker through both screeners with LAZY LOADING.

        OPTIMIZATION: Fetches fundamental data first, then only fetches additional
        data (analyst, volatility) if the ticker passes preliminary filters.
        This reduces API calls by ~47% compared to always fetching all data.

        Args:
            ticker: Stock ticker symbol
            undiscovered_params: Parameters for Undiscovered screener
            coiled_spring_params: Parameters for Coiled Spring screener

        Returns:
            Tuple of (undiscovered_result, coiled_spring_result, api_call_count)
            Results are None if ticker doesn't pass the screener
        """
        api_calls = 0
        undiscovered_result = None
        coiled_spring_result = None

        try:
            # STEP 1: Fetch fundamentals (API call #1)
            fundamentals = self.yf_provider.get_fundamentals(ticker)
            api_calls += 1

            # Null check
            if fundamentals is None or not isinstance(fundamentals, dict):
                logger.debug(f"{ticker}: No fundamentals data, skipping")
                return None, None, api_calls

            # STEP 2: LAZY LOADING - Check basic filters BEFORE fetching more data
            if not self._passes_basic_filters(ticker, fundamentals):
                logger.debug(f"{ticker}: Failed basic filters, saved 2 API calls")
                return None, None, api_calls  # Only used 1 API call instead of 3!

            # STEP 3: Conditionally evaluate Undiscovered (if worth it)
            if self._should_evaluate_undiscovered(fundamentals, undiscovered_params):
                try:
                    analyst_data = self.yf_provider.get_analyst_and_insider_data(ticker)
                    api_calls += 1

                    # Null check
                    if analyst_data is None or not isinstance(analyst_data, dict):
                        logger.debug(f"{ticker}: No analyst data, skipping Undiscovered")
                    else:
                        undiscovered_result = self._evaluate_undiscovered(
                            ticker, fundamentals, analyst_data, undiscovered_params
                        )
                        if undiscovered_result:
                            logger.debug(f"{ticker}: PASSED Undiscovered screener")

                except Exception as e:
                    logger.debug(f"{ticker}: Undiscovered evaluation failed: {e}")

            # STEP 4: Conditionally evaluate Coiled Spring (if worth it)
            if self._should_evaluate_coiled_spring(fundamentals):
                try:
                    volatility = self.yf_provider.get_volatility_metrics(ticker)
                    api_calls += 1

                    # Null check
                    if volatility is None or not isinstance(volatility, dict):
                        logger.debug(f"{ticker}: No volatility data, skipping Coiled Spring")
                    else:
                        coiled_spring_result = self._evaluate_coiled_spring(
                            ticker, fundamentals, volatility, coiled_spring_params
                        )
                        if coiled_spring_result:
                            logger.debug(f"{ticker}: PASSED Coiled Spring screener")

                except Exception as e:
                    logger.debug(f"{ticker}: Coiled Spring evaluation failed: {e}")

            return undiscovered_result, coiled_spring_result, api_calls

        except Exception as e:
            # If fundamentals fail, both screeners fail
            logger.debug(f"{ticker}: Fundamentals fetch failed: {e}")
            return None, None, api_calls

    def _evaluate_undiscovered(
        self,
        ticker: str,
        fundamentals: Dict[str, Any],
        analyst_data: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a ticker against Undiscovered screener criteria.

        Args:
            ticker: Stock ticker symbol
            fundamentals: Pre-fetched fundamental data
            analyst_data: Pre-fetched analyst and insider data
            params: Screener parameters

        Returns:
            Result dict if ticker passes, None otherwise
        """
        # Extract parameters
        max_institutional_ownership = params["max_institutional_ownership"]
        max_analyst_coverage = params["max_analyst_coverage"]
        require_insider_buying = params["require_insider_buying"]

        # Apply filters
        inst_ownership = fundamentals.get("institutional_ownership", 100)
        analyst_count = analyst_data.get("analyst_count", 100)
        has_insider_buying = analyst_data.get("has_recent_insider_buying", False)

        # Check if passes screen
        if inst_ownership > max_institutional_ownership:
            return None
        if analyst_count > max_analyst_coverage:
            return None
        if require_insider_buying and not has_insider_buying:
            return None

        # Calculate score (0-100)
        score = self._calculate_undiscovered_score(
            inst_ownership, analyst_count, has_insider_buying, fundamentals
        )

        # Create result
        return {
            "ticker": ticker.upper(),
            "company_name": fundamentals.get("company_name", ticker),
            "sector": fundamentals.get("sector", "Unknown"),
            "current_price": fundamentals.get("current_price"),
            "market_cap": fundamentals.get("market_cap"),
            "score": round(score, 1),
            "institutional_ownership": inst_ownership,
            "analyst_count": analyst_count,
            "has_insider_buying": has_insider_buying,
            "peg_ratio": fundamentals.get("peg_ratio"),
            "eps_growth": fundamentals.get("eps_growth"),
        }

    def _evaluate_coiled_spring(
        self,
        ticker: str,
        fundamentals: Dict[str, Any],
        volatility: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a ticker against Coiled Spring screener criteria.

        Args:
            ticker: Stock ticker symbol
            fundamentals: Pre-fetched fundamental data
            volatility: Pre-fetched volatility metrics
            params: Screener parameters

        Returns:
            Result dict if ticker passes, None otherwise
        """
        # Extract parameters
        max_volatility_30d = params["max_volatility_30d"]
        require_nr7 = params["require_nr7"]
        min_percentile_rank = params["min_percentile_rank"]

        # Apply filters
        has_nr7 = volatility.get("has_nr7", False)
        volatility_30d = volatility.get("volatility_30d")
        volatility_percentile = volatility.get("volatility_percentile")

        # Filter checks
        if require_nr7 and not has_nr7:
            return None
        if volatility_30d is None or volatility_30d > max_volatility_30d:
            return None
        if volatility_percentile is not None and volatility_percentile > min_percentile_rank:
            return None

        # Get consolidation score
        consolidation_score = volatility.get("consolidation_score", 0)

        # Create result
        return {
            "ticker": ticker.upper(),
            "company_name": fundamentals.get("company_name", ticker),
            "sector": fundamentals.get("sector", "Unknown"),
            "current_price": fundamentals.get("current_price"),
            "market_cap": fundamentals.get("market_cap"),
            "score": round(consolidation_score, 1),
            "has_nr7": has_nr7,
            "volatility_30d": round(volatility_30d, 2) if volatility_30d else None,
            "volatility_percentile": round(volatility_percentile, 1) if volatility_percentile else None,
            "current_range": volatility.get("current_range"),
        }

    def run_undiscovered_screener(self, universe: List[str]) -> Dict[str, Any]:
        """
        Run The Undiscovered screener against full universe.

        Args:
            universe: List of ticker symbols to screen

        Returns:
            Dict containing results and metadata
        """
        logger.info("=" * 80)
        logger.info("RUNNING: The Undiscovered Screener")
        logger.info("=" * 80)

        start_time = datetime.now()
        self.metrics['start_time'] = start_time
        screener_api_calls = 0
        results = []
        failed_tickers = []
        not_found_tickers = []  # Track 404s separately

        # Screening parameters (conservative for full universe)
        max_institutional_ownership = 25.0  # < 25%
        max_analyst_coverage = 5  # <= 5 analysts
        require_insider_buying = False  # FIXED: Changed from True - too strict!

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: inst_own<{max_institutional_ownership}%, analysts<={max_analyst_coverage}, insider_buying={require_insider_buying}")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                self._log_progress(i, len(universe), start_time)

            try:
                # Get fundamentals (1 API call)
                fundamentals = self.yf_provider.get_fundamentals(ticker)
                screener_api_calls += 1

                # Get analyst and insider data (1 API call)
                analyst_data = self.yf_provider.get_analyst_and_insider_data(ticker)
                screener_api_calls += 1

                # Apply filters
                inst_ownership = fundamentals.get("institutional_ownership", 100)
                analyst_count = analyst_data.get("analyst_count", 100)
                has_insider_buying = analyst_data.get("has_recent_insider_buying", False)

                # Check if passes screen
                if inst_ownership > max_institutional_ownership:
                    continue
                if analyst_count > max_analyst_coverage:
                    continue
                # Note: insider_buying check removed (require_insider_buying=False)

                # Calculate score (0-100)
                score = self._calculate_undiscovered_score(
                    inst_ownership, analyst_count, has_insider_buying, fundamentals
                )

                # Create result
                result = {
                    "ticker": ticker.upper(),
                    "company_name": fundamentals.get("company_name", ticker),
                    "sector": fundamentals.get("sector", "Unknown"),
                    "current_price": fundamentals.get("current_price"),
                    "market_cap": fundamentals.get("market_cap"),
                    "score": round(score, 1),
                    "institutional_ownership": inst_ownership,
                    "analyst_count": analyst_count,
                    "has_insider_buying": has_insider_buying,
                    "peg_ratio": fundamentals.get("peg_ratio"),
                    "eps_growth": fundamentals.get("eps_growth"),
                }

                results.append(result)

            except Exception as e:
                self._categorize_error(ticker, e, failed_tickers, not_found_tickers)
                continue

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()
        self.metrics['api_calls'] += screener_api_calls

        # Calculate metrics
        actual_rate = (screener_api_calls / execution_time * 60) if execution_time > 0 else 0
        rate_utilization = (actual_rate / 55 * 100) if actual_rate > 0 else 0

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"⚠ Not found (404): {len(not_found_tickers)} tickers")
        logger.info(f"✗ Failed (errors): {len(failed_tickers)} tickers")
        if failed_tickers:
            logger.info(f"   Failed tickers: {', '.join(failed_tickers[:10])}" +
                       (f" ... and {len(failed_tickers) - 10} more" if len(failed_tickers) > 10 else ""))
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")
        logger.info("")
        logger.info("📊 Metrics Summary:")
        logger.info(f"  - API Calls: {screener_api_calls}")
        logger.info(f"  - Actual Rate: {actual_rate:.2f} calls/min")
        logger.info(f"  - Rate Limit Utilization: {rate_utilization:.1f}%")
        logger.info(f"  - Tickers/Second: {(len(universe) / execution_time):.2f}" if execution_time > 0 else "  - Tickers/Second: 0.00")

        return {
            "screener_name": "The Undiscovered",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
            "not_found_count": len(not_found_tickers),
            "execution_time_seconds": round(execution_time, 2),
            "parameters": {
                "max_institutional_ownership": max_institutional_ownership,
                "max_analyst_coverage": max_analyst_coverage,
                "require_insider_buying": require_insider_buying,
            },
            "timestamp": self.run_timestamp.isoformat(),
        }

    def run_coiled_spring_screener(self, universe: List[str]) -> Dict[str, Any]:
        """
        Run The Coiled Spring screener against full universe.

        Args:
            universe: List of ticker symbols to screen

        Returns:
            Dict containing results and metadata
        """
        logger.info("=" * 80)
        logger.info("RUNNING: The Coiled Spring Screener")
        logger.info("=" * 80)

        start_time = datetime.now()
        screener_api_calls = 0
        results = []
        failed_tickers = []
        not_found_tickers = []  # Track 404s separately

        # Screening parameters
        max_volatility_30d = 20.0  # < 20% HV (relaxed from 15%)
        require_nr7 = True  # Must have NR7 pattern
        min_percentile_rank = 30.0  # Bottom 30th percentile (relaxed from 10%)

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: HV30<{max_volatility_30d}%, NR7={require_nr7}, P<{min_percentile_rank}%")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                self._log_progress(i, len(universe), start_time)

            try:
                # Get fundamentals and volatility metrics (2 API calls)
                fundamentals = self.yf_provider.get_fundamentals(ticker)
                screener_api_calls += 1
                volatility = self.yf_provider.get_volatility_metrics(ticker)
                screener_api_calls += 1

                # Apply filters
                has_nr7 = volatility.get("has_nr7", False)
                volatility_30d = volatility.get("volatility_30d")
                volatility_percentile = volatility.get("volatility_percentile")

                # Filter checks
                if require_nr7 and not has_nr7:
                    continue
                if volatility_30d is None or volatility_30d > max_volatility_30d:
                    continue
                if volatility_percentile is not None and volatility_percentile > min_percentile_rank:
                    continue

                # Get consolidation score
                consolidation_score = volatility.get("consolidation_score", 0)

                # Create result
                result = {
                    "ticker": ticker.upper(),
                    "company_name": fundamentals.get("company_name", ticker),
                    "sector": fundamentals.get("sector", "Unknown"),
                    "current_price": fundamentals.get("current_price"),
                    "market_cap": fundamentals.get("market_cap"),
                    "score": round(consolidation_score, 1),
                    "has_nr7": has_nr7,
                    "volatility_30d": round(volatility_30d, 2) if volatility_30d else None,
                    "volatility_percentile": round(volatility_percentile, 1) if volatility_percentile else None,
                    "current_range": volatility.get("current_range"),
                }

                results.append(result)

            except Exception as e:
                self._categorize_error(ticker, e, failed_tickers, not_found_tickers)
                continue

        # Sort by consolidation score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()
        self.metrics['api_calls'] += screener_api_calls

        # Calculate metrics
        actual_rate = (screener_api_calls / execution_time * 60) if execution_time > 0 else 0
        rate_utilization = (actual_rate / 55 * 100) if actual_rate > 0 else 0

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"⚠ Not found (404): {len(not_found_tickers)} tickers")
        logger.info(f"✗ Failed (errors): {len(failed_tickers)} tickers")
        if failed_tickers:
            logger.info(f"   Failed tickers: {', '.join(failed_tickers[:10])}" +
                       (f" ... and {len(failed_tickers) - 10} more" if len(failed_tickers) > 10 else ""))
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")
        logger.info("")
        logger.info("📊 Metrics Summary:")
        logger.info(f"  - API Calls: {screener_api_calls}")
        logger.info(f"  - Actual Rate: {actual_rate:.2f} calls/min")
        logger.info(f"  - Rate Limit Utilization: {rate_utilization:.1f}%")
        logger.info(f"  - Tickers/Second: {(len(universe) / execution_time):.2f}" if execution_time > 0 else "  - Tickers/Second: 0.00")

        return {
            "screener_name": "The Coiled Spring",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
            "not_found_count": len(not_found_tickers),
            "execution_time_seconds": round(execution_time, 2),
            "parameters": {
                "max_volatility_30d": max_volatility_30d,
                "require_nr7": require_nr7,
                "min_percentile_rank": min_percentile_rank,
            },
            "timestamp": self.run_timestamp.isoformat(),
        }

    def _calculate_undiscovered_score(
        self,
        inst_ownership: float,
        analyst_count: int,
        has_insider_buying: bool,
        fundamentals: Dict[str, Any]
    ) -> float:
        """Calculate Undiscovered score (0-100)."""
        score = 0.0

        # Low institutional ownership (40 points)
        if inst_ownership < 10:
            score += 40
        elif inst_ownership < 15:
            score += 30
        elif inst_ownership < 20:
            score += 20
        elif inst_ownership < 25:
            score += 10

        # Low analyst coverage (30 points)
        if analyst_count == 0:
            score += 30
        elif analyst_count <= 2:
            score += 25
        elif analyst_count <= 3:
            score += 20
        elif analyst_count <= 5:
            score += 10

        # Insider buying (30 points)
        if has_insider_buying:
            score += 30

        return round(score, 1)

    def save_to_firestore(self, screener_name: str, data: Dict[str, Any]):
        """
        Save screener results to Firestore.

        Args:
            screener_name: Name of screener (undiscovered, coiled_spring)
            data: Screener results and metadata
        """
        logger.info(f"Saving {screener_name} results to Firestore...")

        try:
            # Document path: screeners/{screener_name}/runs/{date}
            date_str = self.run_timestamp.strftime("%Y-%m-%d")
            doc_ref = (
                self.db
                .collection("screeners")
                .document(screener_name)
                .collection("runs")
                .document(date_str)
            )

            # Convert numpy types to Python types before saving (Firestore compatibility)
            sanitized_data = convert_numpy_types(data)

            # Save results
            doc_ref.set(sanitized_data)

            logger.info(f"✓ Saved to Firestore: screeners/{screener_name}/runs/{date_str}")

            # Cleanup old runs (keep last 30 days)
            self._cleanup_old_runs(screener_name, days=30)

        except Exception as e:
            logger.error(f"✗ Failed to save to Firestore: {e}")
            raise

    def _cleanup_old_runs(self, screener_name: str, days: int = 30):
        """Delete screener runs older than specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")

            # Query old runs
            old_runs = (
                self.db
                .collection("screeners")
                .document(screener_name)
                .collection("runs")
                .where("timestamp", "<", cutoff_date.isoformat())
                .stream()
            )

            deleted_count = 0
            for doc in old_runs:
                doc.reference.delete()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old runs (older than {cutoff_str})")

        except Exception as e:
            logger.warning(f"Failed to cleanup old runs: {e}")

    def run_smart_money_screener(self, universe: List[str]) -> Dict[str, Any]:
        """
        Run The Smart Money screener against full universe.

        Args:
            universe: List of ticker symbols to screen

        Returns:
            Dict containing results and metadata
        """
        logger.info("=" * 80)
        logger.info("RUNNING: The Smart Money Screener")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = []
        failed_tickers = []
        not_found_tickers = []  # Track 404s separately

        # Screening parameters
        min_call_to_put_ratio = 3.0  # >= 3.0x call volume vs put
        unusual_volume_multiplier = 2.0  # >= 2x average volume

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: C/P>={min_call_to_put_ratio}, Volume>={unusual_volume_multiplier}x avg")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                self._log_progress(i, len(universe), start_time)

            try:
                # Get options flow metrics
                options_flow = self.yf_provider.get_options_flow_metrics(ticker)

                # Check for API errors (timeout, rate limit, etc.)
                if options_flow.get("error") is not None:
                    raise Exception(options_flow["error"])

                # Skip if no options data
                if options_flow.get("call_volume") is None or options_flow.get("put_volume") is None:
                    continue

                # Apply filters
                call_to_put = options_flow.get("call_to_put_ratio")
                total_vol = options_flow.get("total_option_volume", 0)
                avg_vol = options_flow.get("avg_30day_volume", 0)

                # Filter: High call-to-put ratio
                if call_to_put is None or call_to_put < min_call_to_put_ratio:
                    continue

                # Filter: Unusual volume
                if avg_vol > 0 and total_vol < (avg_vol * unusual_volume_multiplier):
                    continue

                # Get fundamentals for display
                fundamentals = self.yf_provider.get_fundamentals(ticker)

                # Calculate score (0-100)
                score = self._calculate_smart_money_score(options_flow, min_call_to_put_ratio)

                # Create result
                result = {
                    "ticker": ticker.upper(),
                    "company_name": fundamentals.get("company_name", ticker),
                    "sector": fundamentals.get("sector", "Unknown"),
                    "current_price": fundamentals.get("current_price"),
                    "market_cap": fundamentals.get("market_cap"),
                    "score": round(score, 1),
                    "call_to_put_ratio": round(call_to_put, 2) if call_to_put else None,
                    "call_volume": options_flow.get("call_volume"),
                    "put_volume": options_flow.get("put_volume"),
                    "total_option_volume": total_vol,
                    "avg_30day_volume": avg_vol,
                    "is_unusual_volume": options_flow.get("is_unusual_volume", False),
                }

                results.append(result)

            except Exception as e:
                self._categorize_error(ticker, e, failed_tickers, not_found_tickers)
                continue

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"⚠ Not found (404): {len(not_found_tickers)} tickers")
        logger.info(f"✗ Failed (errors): {len(failed_tickers)} tickers")
        if failed_tickers:
            logger.info(f"   Failed tickers: {', '.join(failed_tickers[:10])}" +
                       (f" ... and {len(failed_tickers) - 10} more" if len(failed_tickers) > 10 else ""))
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")

        return {
            "screener_name": "The Smart Money",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
            "not_found_count": len(not_found_tickers),
            "execution_time_seconds": round(execution_time, 2),
            "parameters": {
                "min_call_to_put_ratio": min_call_to_put_ratio,
                "unusual_volume_multiplier": unusual_volume_multiplier,
            },
            "timestamp": self.run_timestamp.isoformat(),
        }

    def _calculate_smart_money_score(self, options_flow: Dict[str, Any], min_call_to_put_ratio: float) -> float:
        """Calculate Smart Money score (0-100)."""
        score = 0.0

        # Call-to-Put Ratio score (60 points max)
        call_to_put = options_flow.get("call_to_put_ratio", 0)
        if call_to_put >= 5.0:
            score += 60
        elif call_to_put >= 4.0:
            score += 50
        elif call_to_put >= min_call_to_put_ratio:
            ratio_above_min = call_to_put - min_call_to_put_ratio
            max_range = 4.0 - min_call_to_put_ratio
            score += 40 * (ratio_above_min / max_range) if max_range > 0 else 40

        # Unusual Volume score (40 points max)
        is_unusual = options_flow.get("is_unusual_volume", False)
        if is_unusual:
            score += 40
        else:
            # Partial credit based on volume ratio
            total_vol = options_flow.get("total_option_volume", 0)
            avg_vol = options_flow.get("avg_30day_volume", 1)
            volume_ratio = total_vol / avg_vol if avg_vol > 0 else 0
            if volume_ratio >= 2.0:
                score += 40
            elif volume_ratio >= 1.5:
                score += 20

        return round(score, 1)

    def run(self):
        """
        Main execution method with parallel processing and shared data optimization.

        This method processes both screeners simultaneously with:
        - Shared fundamental data (fetched once per ticker)
        - Parallel processing (6 concurrent workers)
        - Optimized rate limiting (58 req/min via token bucket with 2x burst capacity)
        """
        job_start_time = datetime.now()

        logger.info("=" * 80)
        logger.info("REGULAR STOCK SCREENERS - Starting execution")
        logger.info("Screeners: The Undiscovered, The Coiled Spring")
        logger.info(f"Timestamp: {self.run_timestamp}")
        logger.info("Rate limiting: 58 req/min with adaptive exponential backoff")
        logger.info("Parallel processing: 6 concurrent workers (shared data optimization)")
        logger.info("=" * 80)

        try:
            # Get stock universe (measure initialization time)
            logger.info("Step 1: Fetching stock universe...")
            universe_start = datetime.now()
            universe = self.get_full_exchange_universe()
            universe_elapsed = (datetime.now() - universe_start).total_seconds()
            logger.info(f"✓ Universe loaded in {universe_elapsed:.1f}s ({len(universe)} stocks)")

            # Filter out blacklisted (delisted) tickers
            logger.info("Step 1a: Filtering blacklisted tickers...")
            blacklist_start = datetime.now()
            original_count = len(universe)
            universe = [ticker for ticker in universe if not self.delisted_cache.is_blacklisted(ticker)]
            blacklisted_count = original_count - len(universe)
            blacklist_elapsed = (datetime.now() - blacklist_start).total_seconds()

            if blacklisted_count > 0:
                logger.info(f"⊗ Skipped {blacklisted_count} blacklisted tickers (delisted/no data)")
                logger.info(f"✓ Filtered in {blacklist_elapsed:.2f}s ({len(universe)} tickers remaining)")
            else:
                logger.info(f"✓ No blacklisted tickers to skip ({len(universe)} tickers to process)")
            logger.info("")

            # Screener parameters
            undiscovered_params = {
                "max_institutional_ownership": 25.0,
                "max_analyst_coverage": 5,
                "require_insider_buying": False,
            }
            coiled_spring_params = {
                "max_volatility_30d": 20.0,
                "require_nr7": True,
                "min_percentile_rank": 30.0,
            }

            # Process tickers in parallel with shared data
            logger.info("Step 2: Processing tickers through both screeners (parallel)...")
            screening_start = datetime.now()

            undiscovered_results = []
            coiled_spring_results = []
            total_api_calls = 0
            failed_tickers = []
            not_found_tickers = []
            processed_count = 0

            # Use ThreadPoolExecutor for parallel processing (6 workers = optimized)
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit all ticker processing tasks
                future_to_ticker = {
                    executor.submit(
                        self._process_ticker,
                        ticker,
                        undiscovered_params,
                        coiled_spring_params
                    ): ticker
                    for ticker in universe
                }

                # Process completed futures as they finish
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    processed_count += 1

                    # Log progress every 50 tickers
                    if processed_count % 50 == 0:
                        self._log_progress(processed_count, len(universe), screening_start)

                    try:
                        undiscovered_result, coiled_spring_result, api_calls = future.result()
                        total_api_calls += api_calls

                        # Collect results
                        if undiscovered_result:
                            undiscovered_results.append(undiscovered_result)
                        if coiled_spring_result:
                            coiled_spring_results.append(coiled_spring_result)

                    except Exception as e:
                        # Categorize error
                        self._categorize_error(ticker, e, failed_tickers, not_found_tickers)

            # Sort results by score
            undiscovered_results.sort(key=lambda x: x["score"], reverse=True)
            coiled_spring_results.sort(key=lambda x: x["score"], reverse=True)

            screening_elapsed = (datetime.now() - screening_start).total_seconds()
            self.metrics['api_calls'] = total_api_calls

            # Log screening metrics
            actual_rate = (total_api_calls / screening_elapsed * 60) if screening_elapsed > 0 else 0
            rate_utilization = (actual_rate / 55 * 100) if actual_rate > 0 else 0

            logger.info("")
            logger.info("=" * 80)
            logger.info("SCREENING COMPLETE")
            logger.info(f"✓ Undiscovered: {len(undiscovered_results)} stocks passed")
            logger.info(f"✓ Coiled Spring: {len(coiled_spring_results)} stocks passed")
            logger.info(f"⚠ Not found (404): {len(not_found_tickers)} tickers")
            logger.info(f"✗ Failed (errors): {len(failed_tickers)} tickers")
            if failed_tickers:
                logger.info(f"   Failed tickers: {', '.join(failed_tickers[:10])}" +
                           (f" ... and {len(failed_tickers) - 10} more" if len(failed_tickers) > 10 else ""))
            logger.info(f"⏱  Screening time: {screening_elapsed:.1f} seconds")
            logger.info("")

            # Calculate lazy loading optimization savings
            old_api_calls = len(universe) * 3  # Old approach: always 3 API calls per ticker
            api_calls_saved = old_api_calls - total_api_calls
            percent_saved = (api_calls_saved / old_api_calls * 100) if old_api_calls > 0 else 0
            avg_calls_per_ticker = (total_api_calls / len(universe)) if len(universe) > 0 else 0

            logger.info("📊 Screening Metrics:")
            logger.info(f"  - API Calls Made: {total_api_calls}")
            logger.info(f"  - Actual Rate: {actual_rate:.2f} calls/min")
            logger.info(f"  - Rate Limit Utilization: {rate_utilization:.1f}%")
            logger.info(f"  - Tickers/Second: {(len(universe) / screening_elapsed):.2f}" if screening_elapsed > 0 else "  - Tickers/Second: 0.00")
            logger.info(f"  - Avg API Calls/Ticker: {avg_calls_per_ticker:.2f}")
            logger.info("")
            logger.info("🚀 LAZY LOADING OPTIMIZATION:")
            logger.info(f"  - Old Approach (no lazy loading): {old_api_calls:,} API calls (3 per ticker)")
            logger.info(f"  - New Approach (lazy loading): {total_api_calls:,} API calls ({avg_calls_per_ticker:.2f} per ticker)")
            logger.info(f"  - API Calls SAVED: {api_calls_saved:,} ({percent_saved:.1f}% reduction)")
            logger.info(f"  - Estimated Time Saved: {(api_calls_saved / actual_rate):.1f} minutes" if actual_rate > 0 else "  - Estimated Time Saved: N/A")
            logger.info("=" * 80)

            # Step 2a: Add not_found tickers to blacklist
            if not_found_tickers:
                logger.info("")
                logger.info("Step 2a: Adding delisted tickers to blacklist...")
                self.delisted_cache.add_batch_to_blacklist(not_found_tickers, error_type="no_data")
                logger.info(f"✓ Added {len(not_found_tickers)} tickers to blacklist (will skip in future runs)")

                # Log blacklist statistics
                stats = self.delisted_cache.get_statistics()
                logger.info(f"📊 Blacklist Statistics:")
                logger.info(f"  - Total Blacklisted: {stats.get('total_blacklisted', 0)}")
                logger.info(f"  - Error Types: {stats.get('error_types', {})}")

            # Step 3: Save results to Firestore
            logger.info("")
            logger.info("Step 3: Saving results to Firestore...")

            # Save Undiscovered results
            undiscovered_data = {
                "screener_name": "The Undiscovered",
                "results": undiscovered_results[:100],  # Top 100 only
                "total_results": len(undiscovered_results),
                "total_screened": len(universe),
                "failed_count": len(failed_tickers),
                "not_found_count": len(not_found_tickers),
                "execution_time_seconds": round(screening_elapsed, 2),
                "parameters": undiscovered_params,
                "timestamp": self.run_timestamp.isoformat(),
            }
            self.save_to_firestore("undiscovered", undiscovered_data)

            # Save Coiled Spring results
            coiled_spring_data = {
                "screener_name": "The Coiled Spring",
                "results": coiled_spring_results[:100],  # Top 100 only
                "total_results": len(coiled_spring_results),
                "total_screened": len(universe),
                "failed_count": len(failed_tickers),
                "not_found_count": len(not_found_tickers),
                "execution_time_seconds": round(screening_elapsed, 2),
                "parameters": coiled_spring_params,
                "timestamp": self.run_timestamp.isoformat(),
            }
            self.save_to_firestore("coiled_spring", coiled_spring_data)

            # Calculate and log total job execution time
            total_execution_time = (datetime.now() - job_start_time).total_seconds()
            total_minutes = int(total_execution_time // 60)
            total_seconds = int(total_execution_time % 60)

            overall_rate = (total_api_calls / total_execution_time * 60) if total_execution_time > 0 else 0
            overall_utilization = (overall_rate / 55 * 100) if overall_rate > 0 else 0

            logger.info("")
            logger.info("=" * 80)
            logger.info("REGULAR STOCK SCREENERS - Completed successfully")
            logger.info(f"⏱  Total execution time: {total_minutes}m {total_seconds}s ({total_execution_time:.1f} seconds)")
            logger.info("")
            logger.info("📊 Overall Job Metrics:")
            logger.info(f"  - Total API Calls: {total_api_calls}")
            logger.info(f"  - Overall Rate: {overall_rate:.2f} calls/min")
            logger.info(f"  - Rate Limit Utilization: {overall_utilization:.1f}%")
            logger.info(f"  - Total Tickers Processed: {len(universe)}")
            logger.info(f"  - Optimization: Shared data (1 fundamentals fetch per ticker vs 2)")
            logger.info("=" * 80)

            return {"status": "success", "timestamp": self.run_timestamp.isoformat()}

        except Exception as e:
            logger.error(f"✗ Job failed: {e}")
            logger.error(traceback.format_exc())
            return {"status": "error", "error": str(e)}


def main():
    """
    Entry point for Cloud Run Job.

    Accepts batch_number from:
    1. Command line argument: python run_daily_screeners.py 1
    2. Environment variable: BATCH_NUMBER=1
    3. Default: None (legacy mode with representative universe)

    Usage:
        python run_daily_screeners.py        # Legacy mode (109 stocks)
        python run_daily_screeners.py 1      # Batch 1 (A-D, ~1200 stocks)
        python run_daily_screeners.py 2      # Batch 2 (E-J, ~1200 stocks)
        python run_daily_screeners.py 3      # Batch 3 (K-N, ~1200 stocks)
        python run_daily_screeners.py 4      # Batch 4 (O-S, ~1200 stocks)
        python run_daily_screeners.py 5      # Batch 5 (T-Z, ~1200 stocks)
    """
    # Get batch number from command line or environment variable
    batch_number = None

    # Check command line argument first
    if len(sys.argv) > 1:
        try:
            batch_number = int(sys.argv[1])
            if batch_number not in [1, 2, 3, 4, 5]:
                logger.error(f"Invalid batch number: {batch_number}. Must be 1, 2, 3, 4, or 5.")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid batch number: {sys.argv[1]}. Must be an integer.")
            sys.exit(1)

    # Fallback to environment variable
    if batch_number is None and os.getenv("BATCH_NUMBER"):
        try:
            batch_number = int(os.getenv("BATCH_NUMBER"))
            if batch_number not in [1, 2, 3, 4, 5]:
                logger.error(f"Invalid BATCH_NUMBER env var: {batch_number}. Must be 1, 2, 3, 4, or 5.")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid BATCH_NUMBER env var: {os.getenv('BATCH_NUMBER')}. Must be an integer.")
            sys.exit(1)

    # Log execution mode
    if batch_number:
        logger.info(f"Starting Daily Screener Job - BATCH {batch_number}/5")
        logger.info(f"Will screen ~1200 stocks from full NYSE/NASDAQ universe")
    else:
        logger.info("Starting Daily Screener Job - LEGACY MODE")
        logger.info("Will screen ~109 representative stocks (for testing)")

    # Initialize and run job
    job = DailyScreenerJob(batch_number=batch_number)
    result = job.run()

    # Exit with appropriate code
    if result["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
