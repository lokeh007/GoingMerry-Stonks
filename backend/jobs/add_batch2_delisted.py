#!/usr/bin/env python3
"""
Add Batch 2 Delisted Tickers to Blacklist

Adds the 11 delisted tickers identified in Batch 2 run to the blacklist
to prevent future API calls on invalid tickers.

Delisted tickers from Batch 2 error log:
- FNIGX, FOACW, FRFAF, FSTWF, FTPSF, FVGPY
- GACW, GADA, GAFC, GBNXY, GDEL

Usage:
    python backend/jobs/add_batch2_delisted.py
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
    """Add Batch 2 delisted tickers to blacklist."""

    # Delisted tickers from Batch 2 error log (from November 13, 2025 run)
    delisted_tickers = [
        "FNIGX",   # No price data available
        "FOACW",   # No price data available
        "FRFAF",   # No price data available
        "FSTWF",   # No price data available
        "FTPSF",   # No price data available
        "FVGPY",   # No price data available
        "GACW",    # No price data available
        "GADA",    # No price data available
        "GAFC",    # No price data available
        "GBNXY",   # No price data available
        "GDEL",    # No price data available
    ]

    logger.info("=" * 80)
    logger.info("Adding Batch 2 Delisted Tickers to Blacklist")
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

    # Add batch to blacklist
    logger.info("Adding tickers to blacklist...")
    cache.add_batch_to_blacklist(delisted_tickers, error_type="no_data")

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
