#!/usr/bin/env python3
"""
Add Batch 3 Delisted Tickers to Blacklist

Adds the 9 delisted tickers identified in Batch 3 run to the blacklist
to prevent future API calls on invalid tickers.

Delisted tickers from Batch 3 error log:
- MMTX, MNZLY, MOVAA, MPJS, MRCA, MREGY, MROSY, MRUWY, LOMWF

Usage:
    python backend/jobs/add_batch3_delisted.py
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.delisted_ticker_cache import DelistedTickerCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Add Batch 3 delisted tickers to blacklist."""

    # Delisted tickers from Batch 3 error log (from November 16, 2025 run)
    delisted_tickers = [
        "MMTX",    # No price data available
        "MNZLY",   # No price data available
        "MOVAA",   # No price data available
        "MPJS",    # No price data available
        "MRCA",    # No price data available
        "MREGY",   # No price data available
        "MROSY",   # No price data available
        "MRUWY",   # No price data available
        "LOMWF",   # No price data available
    ]

    logger.info("=" * 80)
    logger.info("Adding Batch 3 Delisted Tickers to Blacklist")
    logger.info("=" * 80)
    logger.info(f"Tickers to add: {len(delisted_tickers)}")
    logger.info(f"Tickers: {', '.join(delisted_tickers)}")
    logger.info("")

    # Initialize cache
    cache = DelistedTickerCache(ttl_days=30)

    # Check which are already blacklisted
    already_blacklisted = []
    for ticker in delisted_tickers:
        if cache.is_blacklisted(ticker):
            already_blacklisted.append(ticker)

    if already_blacklisted:
        logger.info(f"Already blacklisted ({len(already_blacklisted)}): {', '.join(already_blacklisted)}")
        logger.info("")

    # Add tickers to blacklist individually to preserve failure counts
    logger.info("Adding tickers to blacklist (preserving failure counts)...")
    for ticker in delisted_tickers:
        cache.add_to_blacklist(ticker, error_type="no_data")

    logger.info("✓ Successfully added tickers to blacklist")
    logger.info("")

    # Get statistics
    stats = cache.get_statistics()
    logger.info("📊 Blacklist Statistics:")
    logger.info(f"  - Total Blacklisted: {stats.get('total_blacklisted', 0)}")
    logger.info(f"  - Error Types: {stats.get('error_types', {})}")
    logger.info(f"  - Avg Failures/Ticker: {stats.get('avg_failures_per_ticker', 0):.1f}")
    logger.info("")

    logger.info("=" * 80)
    logger.info("✓ Complete - These tickers will be skipped in future runs")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
