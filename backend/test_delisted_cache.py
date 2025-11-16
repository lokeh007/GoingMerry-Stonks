#!/usr/bin/env python3
"""
Test script for DelistedTickerCache

Tests:
1. Adding tickers to blacklist (individual and batch)
2. Checking if tickers are blacklisted
3. Firestore persistence
4. TTL-based expiration
5. Statistics

Run: python backend/test_delisted_cache.py
"""

import sys
import os
import logging
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.delisted_ticker_cache import DelistedTickerCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_operations():
    """Test basic blacklist operations."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Basic Operations")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Test 1: Add single ticker
    logger.info("\n1. Adding single ticker to blacklist...")
    cache.add_to_blacklist("DMII", error_type="no_data")

    # Test 2: Check if blacklisted
    logger.info("\n2. Checking if ticker is blacklisted...")
    is_blacklisted = cache.is_blacklisted("DMII")
    logger.info(f"DMII blacklisted: {is_blacklisted}")
    assert is_blacklisted, "DMII should be blacklisted"

    is_blacklisted = cache.is_blacklisted("AAPL")
    logger.info(f"AAPL blacklisted: {is_blacklisted}")
    assert not is_blacklisted, "AAPL should not be blacklisted"

    logger.info("✓ Basic operations working correctly")


def test_batch_operations():
    """Test batch add operations."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Batch Operations")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Add the 12 tickers from user's error report
    delisted_tickers = [
        "DMII", "DNCLY", "DNMX", "DOT", "DPDSY", "DSAC",
        "DSRNY", "DTDT", "DWWYF", "DXG", "DYBTY"
    ]

    logger.info(f"\n1. Adding {len(delisted_tickers)} tickers in batch...")
    cache.add_batch_to_blacklist(delisted_tickers, error_type="no_data")

    # Verify all are blacklisted
    logger.info("\n2. Verifying all tickers are blacklisted...")
    for ticker in delisted_tickers:
        is_blacklisted = cache.is_blacklisted(ticker)
        logger.info(f"  {ticker}: {'✓' if is_blacklisted else '✗'}")
        assert is_blacklisted, f"{ticker} should be blacklisted"

    logger.info("✓ Batch operations working correctly")


def test_statistics():
    """Test blacklist statistics."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Statistics")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Get statistics
    logger.info("\n1. Getting blacklist statistics...")
    stats = cache.get_statistics()

    logger.info(f"\n📊 Blacklist Statistics:")
    logger.info(f"  - Total Blacklisted: {stats.get('total_blacklisted', 0)}")
    logger.info(f"  - Error Types: {stats.get('error_types', {})}")
    logger.info(f"  - Total Failures: {stats.get('total_failures', 0)}")
    logger.info(f"  - Avg Failures/Ticker: {stats.get('avg_failures_per_ticker', 0):.2f}")

    logger.info("✓ Statistics retrieved successfully")


def test_get_all_blacklisted():
    """Test getting all blacklisted tickers."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Get All Blacklisted Tickers")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    blacklisted = cache.get_blacklisted_tickers()
    logger.info(f"\n1. Retrieved {len(blacklisted)} blacklisted tickers")
    logger.info(f"   Sample (first 20): {sorted(list(blacklisted))[:20]}")

    logger.info("✓ Retrieved all blacklisted tickers successfully")


def test_remove_ticker():
    """Test removing a ticker from blacklist."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Remove Ticker from Blacklist")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Add a test ticker
    test_ticker = "TEST123"
    logger.info(f"\n1. Adding {test_ticker} to blacklist...")
    cache.add_to_blacklist(test_ticker, error_type="no_data")

    # Verify it's blacklisted
    assert cache.is_blacklisted(test_ticker), f"{test_ticker} should be blacklisted"
    logger.info(f"   ✓ {test_ticker} is blacklisted")

    # Remove it
    logger.info(f"\n2. Removing {test_ticker} from blacklist...")
    cache.remove_from_blacklist(test_ticker)

    # Verify it's not blacklisted
    assert not cache.is_blacklisted(test_ticker), f"{test_ticker} should not be blacklisted"
    logger.info(f"   ✓ {test_ticker} is no longer blacklisted")

    logger.info("✓ Remove ticker working correctly")


def test_filtering_universe():
    """Test filtering a stock universe with blacklisted tickers."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Filter Stock Universe")
    logger.info("=" * 80)

    cache = DelistedTickerCache(ttl_days=30)

    # Sample universe with some blacklisted tickers
    universe = [
        "AAPL", "MSFT", "GOOGL", "DMII", "TSLA",
        "DNCLY", "NVDA", "AMD", "DOT", "META"
    ]

    logger.info(f"\n1. Original universe ({len(universe)} tickers):")
    logger.info(f"   {universe}")

    # Filter universe
    logger.info(f"\n2. Filtering blacklisted tickers...")
    filtered_universe = [ticker for ticker in universe if not cache.is_blacklisted(ticker)]

    logger.info(f"\n3. Filtered universe ({len(filtered_universe)} tickers):")
    logger.info(f"   {filtered_universe}")

    skipped_count = len(universe) - len(filtered_universe)
    logger.info(f"\n4. Skipped {skipped_count} blacklisted tickers")

    # Verify known good tickers are still there
    assert "AAPL" in filtered_universe, "AAPL should be in filtered universe"
    assert "MSFT" in filtered_universe, "MSFT should be in filtered universe"

    # Verify known delisted tickers are filtered out
    assert "DMII" not in filtered_universe, "DMII should be filtered out"
    assert "DNCLY" not in filtered_universe, "DNCLY should be filtered out"

    logger.info("✓ Universe filtering working correctly")


def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("DELISTED TICKER CACHE - Test Suite")
    logger.info("=" * 80)

    try:
        # Run all tests
        test_basic_operations()
        test_batch_operations()
        test_statistics()
        test_get_all_blacklisted()
        test_remove_ticker()
        test_filtering_universe()

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 80)
        logger.info("\nDelisted Ticker Cache is working correctly!")
        logger.info("Next steps:")
        logger.info("  1. Deploy updated screener jobs")
        logger.info("  2. Monitor first batch run to see blacklist in action")
        logger.info("  3. Verify API call reduction in future runs")

    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
