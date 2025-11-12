#!/usr/bin/env python3
"""
Daily Stock Screeners - Cloud Run Job (Batched Execution)

Runs The Undiscovered, The Coiled Spring, and Smart Money screeners against the full
NYSE + NASDAQ universe (~6000 stocks) in 3 batches to respect yfinance rate limits.

Batch Schedule:
- Batch 1: 4:30 PM ET - Tickers A-H (~2000 stocks)
- Batch 2: 5:30 PM ET - Tickers I-P (~2000 stocks)
- Batch 3: 6:30 PM ET - Tickers Q-Z (~2000 stocks)

Estimated runtime per batch: 60-80 minutes
Data sources: SEC EDGAR + NASDAQ FTP (free, no API keys required)
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore
from app.services.yfinance_provider import YFinanceProvider
from app.services.ticker_universe import TickerUniverseProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyScreenerJob:
    """Orchestrates daily screener execution and Firestore storage."""

    def __init__(self, batch_number: Optional[int] = None):
        """
        Initialize Firestore client and yfinance provider.

        Args:
            batch_number: Batch number (1, 2, or 3) for staggered execution.
                         If None, uses representative universe (legacy mode).
        """
        self.db = firestore.Client()
        self.yf_provider = YFinanceProvider()
        self.ticker_provider = TickerUniverseProvider()
        self.run_timestamp = datetime.now(timezone.utc)
        self.batch_number = batch_number

        if batch_number:
            logger.info(f"Initializing Daily Screener Job - Batch {batch_number}/3")

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
            - Batch mode: ~2000 stocks per batch
            - Legacy mode: ~109 representative stocks
        """
        if self.batch_number:
            # Batched execution: Get stocks for this specific batch
            logger.info(f"Fetching batch {self.batch_number}/3 from full NYSE + NASDAQ universe...")
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
        results = []
        failed_tickers = []

        # Screening parameters (conservative for full universe)
        max_institutional_ownership = 25.0  # < 25%
        max_analyst_coverage = 5  # <= 5 analysts
        require_insider_buying = False  # FIXED: Changed from True - too strict!

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: inst_own<{max_institutional_ownership}%, analysts<={max_analyst_coverage}, insider_buying={require_insider_buying}")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(universe)} stocks processed")

            try:
                # Get fundamentals
                fundamentals = self.yf_provider.get_fundamentals(ticker)

                # Get analyst and insider data
                analyst_data = self.yf_provider.get_analyst_and_insider_data(ticker)

                # Apply filters
                inst_ownership = fundamentals.get("institutional_ownership", 100)
                analyst_count = analyst_data.get("analyst_count", 100)
                has_insider_buying = analyst_data.get("has_recent_insider_buying", False)

                # Check if passes screen
                if inst_ownership > max_institutional_ownership:
                    continue
                if analyst_count > max_analyst_coverage:
                    continue
                if require_insider_buying and not has_insider_buying:
                    continue

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
                logger.debug(f"Failed to screen {ticker}: {e}")
                failed_tickers.append(ticker)
                continue

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"✗ Failed/skipped: {len(failed_tickers)} stocks")
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")

        return {
            "screener_name": "The Undiscovered",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
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
        results = []
        failed_tickers = []

        # Screening parameters
        max_volatility_30d = 20.0  # < 20% HV (relaxed from 15%)
        require_nr7 = True  # Must have NR7 pattern
        min_percentile_rank = 30.0  # Bottom 30th percentile (relaxed from 10%)

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: HV30<{max_volatility_30d}%, NR7={require_nr7}, P<{min_percentile_rank}%")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(universe)} stocks processed")

            try:
                # Get fundamentals and volatility metrics
                fundamentals = self.yf_provider.get_fundamentals(ticker)
                volatility = self.yf_provider.get_volatility_metrics(ticker)

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
                logger.debug(f"Failed to screen {ticker}: {e}")
                failed_tickers.append(ticker)
                continue

        # Sort by consolidation score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"✗ Failed/skipped: {len(failed_tickers)} stocks")
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")

        return {
            "screener_name": "The Coiled Spring",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
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

            # Save results
            doc_ref.set(data)

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

        # Screening parameters
        min_call_to_put_ratio = 3.0  # >= 3.0x call volume vs put
        unusual_volume_multiplier = 2.0  # >= 2x average volume

        logger.info(f"Screening {len(universe)} stocks...")
        logger.info(f"Parameters: C/P>={min_call_to_put_ratio}, Volume>={unusual_volume_multiplier}x avg")

        for i, ticker in enumerate(universe, 1):
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(universe)} stocks processed")

            try:
                # Get options flow metrics
                options_flow = self.yf_provider.get_options_flow_metrics(ticker)

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
                logger.debug(f"Failed to screen {ticker}: {e}")
                failed_tickers.append(ticker)
                continue

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✓ Screening complete: {len(results)} stocks passed")
        logger.info(f"✗ Failed/skipped: {len(failed_tickers)} stocks")
        logger.info(f"⏱  Execution time: {execution_time:.1f} seconds")

        return {
            "screener_name": "The Smart Money",
            "results": results[:100],  # Top 100 only
            "total_results": len(results),
            "total_screened": len(universe),
            "failed_count": len(failed_tickers),
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
        """Main execution method."""
        logger.info("=" * 80)
        logger.info("DAILY STOCK SCREENERS - Starting execution")
        logger.info(f"Timestamp: {self.run_timestamp}")
        logger.info("=" * 80)

        try:
            # Get stock universe
            universe = self.get_full_exchange_universe()

            # Run screeners
            screeners = [
                ("undiscovered", self.run_undiscovered_screener),
                ("coiled_spring", self.run_coiled_spring_screener),
                ("smart_money", self.run_smart_money_screener),
            ]

            for screener_name, screener_func in screeners:
                try:
                    # Run screener
                    results = screener_func(universe)

                    # Save to Firestore
                    self.save_to_firestore(screener_name, results)

                except Exception as e:
                    logger.error(f"✗ Failed to run {screener_name}: {e}")
                    logger.error(traceback.format_exc())
                    continue

            logger.info("=" * 80)
            logger.info("DAILY STOCK SCREENERS - Completed successfully")
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
        python run_daily_screeners.py 1      # Batch 1 (A-H, ~2000 stocks)
        python run_daily_screeners.py 2      # Batch 2 (I-P, ~2000 stocks)
        python run_daily_screeners.py 3      # Batch 3 (Q-Z, ~2000 stocks)
    """
    # Get batch number from command line or environment variable
    batch_number = None

    # Check command line argument first
    if len(sys.argv) > 1:
        try:
            batch_number = int(sys.argv[1])
            if batch_number not in [1, 2, 3]:
                logger.error(f"Invalid batch number: {batch_number}. Must be 1, 2, or 3.")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid batch number: {sys.argv[1]}. Must be an integer.")
            sys.exit(1)

    # Fallback to environment variable
    if batch_number is None and os.getenv("BATCH_NUMBER"):
        try:
            batch_number = int(os.getenv("BATCH_NUMBER"))
            if batch_number not in [1, 2, 3]:
                logger.error(f"Invalid BATCH_NUMBER env var: {batch_number}. Must be 1, 2, or 3.")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid BATCH_NUMBER env var: {os.getenv('BATCH_NUMBER')}. Must be an integer.")
            sys.exit(1)

    # Log execution mode
    if batch_number:
        logger.info(f"Starting Daily Screener Job - BATCH {batch_number}/3")
        logger.info(f"Will screen ~2000 stocks from full NYSE/NASDAQ universe")
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
