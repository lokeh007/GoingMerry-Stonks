#!/usr/bin/env python3
"""
Populate Delisted Ticker Blacklist - One-Time Utility

Proactively checks all tickers in the universe to identify delisted/invalid stocks
and populate the blacklist BEFORE running expensive screeners.

Benefits:
- Saves API calls on first screener run
- Identifies all delisted tickers upfront
- Provides statistics on universe quality

Estimated Runtime:
- ~6000 tickers / 50 req/min = ~120 minutes (2 hours)
- Can be interrupted and resumed (already-blacklisted tickers are skipped)

Usage:
    python backend/jobs/populate_delisted_blacklist.py

Options:
    --batch N         Process only batch N (1-5) instead of full universe
    --dry-run         Check tickers but don't add to blacklist
    --rate-limit N    Set rate limit (default: 50 req/min)
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Set

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore
from app.services.yfinance_provider import YFinanceProvider
from app.services.ticker_universe import TickerUniverseProvider
from app.services.delisted_ticker_cache import DelistedTickerCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DelistedTickerScanner:
    """Scans ticker universe to identify delisted stocks."""

    def __init__(self, rate_limit: int = 50, dry_run: bool = False):
        """
        Initialize scanner.

        Args:
            rate_limit: Max API calls per minute (default: 50)
            dry_run: If True, check tickers but don't add to blacklist
        """
        self.yf_provider = YFinanceProvider(max_requests_per_minute=rate_limit)
        self.ticker_provider = TickerUniverseProvider()
        self.delisted_cache = DelistedTickerCache(ttl_days=30)
        self.dry_run = dry_run
        self.rate_limit = rate_limit

        # Statistics
        self.stats = {
            'total_checked': 0,
            'already_blacklisted': 0,
            'valid_tickers': 0,
            'delisted_found': 0,
            'errors': 0,
            'start_time': None,
        }

    def is_ticker_valid(self, ticker: str) -> tuple[bool, str]:
        """
        Check if ticker has valid data with minimal API calls.

        Uses YFinanceProvider service (respects rate limiting and has adaptive backoff).
        Only checks ticker.info (1 API call) - much faster than full fundamentals.

        Args:
            ticker: Ticker symbol to check

        Returns:
            Tuple of (is_valid, error_type)
            - is_valid: True if ticker has data, False if delisted/invalid
            - error_type: "no_data", "404", "timeout", "rate_limit", or None
        """
        try:
            # Lightweight check using ticker_details (1 API call vs 2-3 for get_fundamentals)
            # This is ~3x faster but still uses YFinanceProvider with rate limiting
            details = self.yf_provider.get_ticker_details(ticker)

            # Check if we got any meaningful data
            if not details:
                return False, "no_data"

            # Valid tickers will have at least a company name or market cap
            has_name = details.get("longName") or details.get("shortName")
            has_market_cap = details.get("marketCap") is not None
            has_price = details.get("currentPrice") or details.get("regularMarketPrice")

            # If we have at least one of these, ticker is valid
            if has_name or has_market_cap or has_price:
                return True, None
            else:
                return False, "no_data"

        except Exception as e:
            error_msg = str(e).lower()

            # Categorize error
            if '404' in error_msg or 'not found' in error_msg:
                return False, "404"
            elif 'no data' in error_msg or 'no fundamentals' in error_msg:
                return False, "no_data"
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                return False, "timeout"
            elif 'rate limit' in error_msg or 'too many' in error_msg:
                return False, "rate_limit"
            else:
                # Unknown error - log but don't blacklist
                logger.debug(f"Unknown error for {ticker}: {error_msg}")
                return False, "error"

    def scan_universe(
        self,
        batch_number: int = None,
        resume: bool = True
    ) -> Dict[str, any]:
        """
        Scan ticker universe to identify delisted stocks.

        Args:
            batch_number: If set, only scan this batch (1-5)
            resume: If True, skip already-blacklisted tickers

        Returns:
            Dict with scan results and statistics
        """
        self.stats['start_time'] = datetime.now()

        logger.info("=" * 80)
        logger.info("DELISTED TICKER SCANNER - Starting")
        logger.info("=" * 80)
        logger.info(f"Rate limit: {self.rate_limit} req/min")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Resume mode: {resume}")
        logger.info("")

        # Get universe
        if batch_number:
            logger.info(f"Loading batch {batch_number}/5...")
            universe = self.ticker_provider.get_batch_universe(batch_number)
        else:
            logger.info("Loading full universe...")
            universe = self.ticker_provider.get_full_universe()

        logger.info(f"✓ Loaded {len(universe)} tickers")
        logger.info("")

        # Get already-blacklisted tickers if resuming
        already_blacklisted = set()
        if resume:
            already_blacklisted = self.delisted_cache.get_blacklisted_tickers()
            logger.info(f"Resuming: {len(already_blacklisted)} tickers already blacklisted")
            logger.info("")

        # Estimate time
        tickers_to_check = len(universe) - len(already_blacklisted) if resume else len(universe)
        estimated_minutes = tickers_to_check / self.rate_limit
        logger.info(f"Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")
        logger.info("")

        # Scan tickers
        delisted_tickers = []
        valid_tickers = []
        error_tickers = []

        logger.info("Starting scan...")
        logger.info("=" * 80)

        for i, ticker in enumerate(universe, 1):
            # Skip already blacklisted
            if resume and ticker in already_blacklisted:
                self.stats['already_blacklisted'] += 1
                continue

            self.stats['total_checked'] += 1

            # Check ticker validity
            is_valid, error_type = self.is_ticker_valid(ticker)

            if is_valid:
                valid_tickers.append(ticker)
                self.stats['valid_tickers'] += 1
            elif error_type in ['no_data', '404', 'not_found']:
                delisted_tickers.append(ticker)
                self.stats['delisted_found'] += 1
                logger.info(f"⊗ {ticker}: DELISTED ({error_type})")
            else:
                error_tickers.append(ticker)
                self.stats['errors'] += 1

            # Progress update every 50 tickers
            if i % 50 == 0:
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                rate = self.stats['total_checked'] / elapsed if elapsed > 0 else 0
                remaining = tickers_to_check - self.stats['total_checked']
                eta_seconds = remaining / rate if rate > 0 else 0

                logger.info("")
                logger.info(f"Progress: {i}/{len(universe)} ({i/len(universe)*100:.1f}%)")
                logger.info(f"  Checked: {self.stats['total_checked']}")
                logger.info(f"  Valid: {self.stats['valid_tickers']}")
                logger.info(f"  Delisted: {self.stats['delisted_found']}")
                logger.info(f"  Skipped (already blacklisted): {self.stats['already_blacklisted']}")
                logger.info(f"  Rate: {rate*60:.1f} tickers/min")
                logger.info(f"  ETA: {eta_seconds/60:.1f} minutes")
                logger.info("")

        # Add delisted tickers to blacklist
        if delisted_tickers and not self.dry_run:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Adding {len(delisted_tickers)} delisted tickers to blacklist...")
            self.delisted_cache.add_batch_to_blacklist(delisted_tickers, error_type="no_data")
            logger.info("✓ Blacklist updated")
        elif delisted_tickers and self.dry_run:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"DRY RUN: Would add {len(delisted_tickers)} tickers to blacklist:")
            logger.info(f"  {', '.join(delisted_tickers[:20])}")
            if len(delisted_tickers) > 20:
                logger.info(f"  ... and {len(delisted_tickers) - 20} more")

        # Final statistics
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()

        logger.info("")
        logger.info("=" * 80)
        logger.info("SCAN COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total universe: {len(universe)} tickers")
        logger.info(f"Already blacklisted: {self.stats['already_blacklisted']} (skipped)")
        logger.info(f"Checked: {self.stats['total_checked']} tickers")
        logger.info(f"  ✓ Valid: {self.stats['valid_tickers']} ({self.stats['valid_tickers']/self.stats['total_checked']*100:.1f}%)")
        logger.info(f"  ⊗ Delisted: {self.stats['delisted_found']} ({self.stats['delisted_found']/self.stats['total_checked']*100:.1f}%)")
        logger.info(f"  ✗ Errors: {self.stats['errors']}")
        logger.info(f"Execution time: {elapsed/60:.1f} minutes")
        logger.info("")

        # Get final blacklist statistics
        blacklist_stats = self.delisted_cache.get_statistics()
        logger.info("📊 Final Blacklist Statistics:")
        logger.info(f"  - Total Blacklisted: {blacklist_stats.get('total_blacklisted', 0)}")
        logger.info(f"  - Error Types: {blacklist_stats.get('error_types', {})}")
        logger.info("")

        if not self.dry_run:
            logger.info("✓ Future screener runs will skip these tickers automatically!")

        logger.info("=" * 80)

        return {
            'universe_size': len(universe),
            'valid_tickers': valid_tickers,
            'delisted_tickers': delisted_tickers,
            'error_tickers': error_tickers,
            'statistics': self.stats,
        }


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Scan ticker universe to identify and blacklist delisted stocks'
    )
    parser.add_argument(
        '--batch',
        type=int,
        choices=[1, 2, 3, 4, 5],
        help='Process only this batch (1-5) instead of full universe'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check tickers but don\'t add to blacklist'
    )
    parser.add_argument(
        '--rate-limit',
        type=int,
        default=50,
        help='Max API calls per minute (default: 50)'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Re-check already blacklisted tickers'
    )

    args = parser.parse_args()

    # Initialize scanner
    scanner = DelistedTickerScanner(
        rate_limit=args.rate_limit,
        dry_run=args.dry_run
    )

    # Run scan
    try:
        results = scanner.scan_universe(
            batch_number=args.batch,
            resume=not args.no_resume
        )

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n\n⚠ Scan interrupted by user")
        logger.info("Progress has been saved. Run again to resume.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Scan failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
