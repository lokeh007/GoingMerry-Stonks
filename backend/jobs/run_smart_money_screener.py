#!/usr/bin/env python3
"""
Smart Money Screener (Options Flow) - Cloud Run Job (Batched Execution)

Runs ONLY The Smart Money (options flow) screener against the full NYSE + NASDAQ
universe (~6000 stocks) in 5 batches with reduced rate limits (45 req/min).

This screener is separated from regular screeners due to higher API token consumption
(3 tokens per ticker for options data vs 2 tokens for regular screeners).

Batch Schedule (Sequential - runs AFTER regular screeners complete):
- Batch 1: 12:00 AM ET - Tickers A-D (~1200 stocks)
- Batch 2: 2:00 AM ET - Tickers E-J (~1200 stocks)
- Batch 3: 4:00 AM ET - Tickers K-N (~1200 stocks)
- Batch 4: 6:00 AM ET - Tickers O-S (~1200 stocks)
- Batch 5: 8:00 AM ET - Tickers T-Z (~1200 stocks)

Estimated runtime per batch: ~120 minutes (2 hours)
Rate limit: 45 requests/minute (vs 60 req/min for regular screeners)
Data sources: Yahoo Finance (free, no API keys required)
"""

import os
import sys
import logging
import re
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


class SmartMoneyScreenerJob:
    """Orchestrates Smart Money (options flow) screener execution and Firestore storage."""

    # Compile regex once at class level for performance
    _404_PATTERN = re.compile(r'\b404\b')

    def __init__(self, batch_number: Optional[int] = None):
        """
        Initialize Firestore client and yfinance provider with reduced rate limit.

        Args:
            batch_number: Batch number (1-5) for staggered execution.
                         If None, uses representative universe (legacy mode).
        """
        self.db = firestore.Client()
        # IMPORTANT: Use reduced rate limit (45 req/min) for options flow screener
        self.yf_provider = YFinanceProvider(rate_limit=45, burst_capacity=15)
        self.ticker_provider = TickerUniverseProvider()
        self.run_timestamp = datetime.now(timezone.utc)
        self.batch_number = batch_number

        if batch_number:
            logger.info(f"Initializing Smart Money Screener Job - Batch {batch_number}/5")
            logger.info(f"Rate limit: 45 requests/minute (reduced for options data)")

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
            'no fundamentals' in error_msg or
            'no options' in error_msg
        )

        # Check if it's a rate limit or timeout error
        is_rate_limit = 'rate limit' in error_msg or 'too many requests' in error_msg
        is_timeout = 'timeout' in error_msg or 'timed out' in error_msg

        if is_404:
            # Expected - ticker doesn't exist or no options data available
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
        Get representative universe for testing (smaller sample).

        In production, replace with full NYSE/NASDAQ API call.
        """
        # Start with existing universes
        popular = self.yf_provider.get_stock_universe("popular")
        sp500_sample = self.yf_provider.get_stock_universe("sp500_sample")
        tech = self.yf_provider.get_stock_universe("tech")

        # Combine and deduplicate
        universe = list(set(popular + sp500_sample + tech))

        logger.info(f"Representative universe: {len(universe)} stocks (MVP mode)")
        logger.warning("Production deployment should use full NYSE/NASDAQ API")

        return universe

    def run_smart_money_screener(self, universe: List[str]) -> Dict[str, Any]:
        """
        Run The Smart Money screener against full universe.

        Args:
            universe: List of ticker symbols to screen

        Returns:
            Dict containing results and metadata
        """
        logger.info("=" * 80)
        logger.info("RUNNING: The Smart Money Screener (Options Flow)")
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
                "rate_limit": 45,  # Document the rate limit used
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

    def save_to_firestore(self, screener_name: str, data: Dict[str, Any]):
        """
        Save screener results to Firestore.

        Args:
            screener_name: Name of screener (smart_money)
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

    def run(self):
        """Main execution method."""
        job_start_time = datetime.now()

        logger.info("=" * 80)
        logger.info("SMART MONEY SCREENER (OPTIONS FLOW) - Starting execution")
        logger.info(f"Timestamp: {self.run_timestamp}")
        logger.info(f"Rate limit: 45 requests/minute")
        logger.info("=" * 80)

        try:
            # Get stock universe
            universe = self.get_full_exchange_universe()

            # Run Smart Money screener only
            try:
                results = self.run_smart_money_screener(universe)

                # Save to Firestore
                self.save_to_firestore("smart_money", results)

            except Exception as e:
                logger.error(f"✗ Failed to run smart_money screener: {e}")
                logger.error(traceback.format_exc())
                raise

            # Calculate and log total job execution time
            total_execution_time = (datetime.now() - job_start_time).total_seconds()
            total_minutes = int(total_execution_time // 60)
            total_seconds = int(total_execution_time % 60)

            logger.info("=" * 80)
            logger.info("SMART MONEY SCREENER (OPTIONS FLOW) - Completed successfully")
            logger.info(f"⏱  Total execution time: {total_minutes}m {total_seconds}s ({total_execution_time:.1f} seconds)")
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
    1. Command line argument: python run_smart_money_screener.py 1
    2. Environment variable: BATCH_NUMBER=1
    3. Default: None (legacy mode with representative universe)

    Usage:
        python run_smart_money_screener.py        # Legacy mode (~109 stocks)
        python run_smart_money_screener.py 1      # Batch 1 (A-D, ~1200 stocks)
        python run_smart_money_screener.py 2      # Batch 2 (E-J, ~1200 stocks)
        python run_smart_money_screener.py 3      # Batch 3 (K-N, ~1200 stocks)
        python run_smart_money_screener.py 4      # Batch 4 (O-S, ~1200 stocks)
        python run_smart_money_screener.py 5      # Batch 5 (T-Z, ~1200 stocks)
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
        logger.info(f"Starting Smart Money Screener Job - BATCH {batch_number}/5")
        logger.info(f"Will screen ~1200 stocks from full NYSE/NASDAQ universe")
    else:
        logger.info("Starting Smart Money Screener Job - LEGACY MODE")
        logger.info("Will screen ~109 representative stocks (for testing)")

    # Initialize and run job
    job = SmartMoneyScreenerJob(batch_number=batch_number)
    result = job.run()

    # Exit with appropriate code
    if result["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
