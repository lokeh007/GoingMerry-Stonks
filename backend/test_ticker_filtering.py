#!/usr/bin/env python3
"""
Test script to validate ticker filtering improvements.

This tests that the ETF filtering whitelist approach correctly:
1. Keeps legitimate stocks (no false positives)
2. Filters out known ETFs (no false negatives)
"""

import logging
from app.services.ticker_universe import TickerUniverseProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_legitimate_stocks_not_filtered():
    """Test that legitimate stocks are NOT filtered out."""

    provider = TickerUniverseProvider()

    # Stocks that were being falsely filtered by the old pattern matching
    test_cases = [
        # Ending in X, Z, L, S, M (old suffix pattern)
        ("AES", "AES Corporation - Fortune 200 utility"),
        ("CMS", "CMS Energy - S&P 500 utility"),
        ("TGS", "TGS ASA - Seismic data provider"),
        ("AOS", "A.O. Smith - S&P 500 water heater manufacturer"),
        ("GMS", "GMS Inc. - Building materials distributor"),
        ("LXS", "Luxfer Holdings - Materials company"),
        ("SMS", "SMS Co. - Industrial distributor"),
        ("FLEX", "Flex Ltd. - Electronics manufacturer"),
        ("CEIX", "CONSOL Energy - Coal producer"),
        ("AIZ", "Assurant Inc. - Insurance company"),

        # Starting with D, T, U, S (old prefix pattern)
        ("DFS", "Discover Financial Services - $32B market cap, S&P 500"),
        ("DHI", "D.R. Horton - $42B market cap, largest homebuilder"),
        ("DOW", "Dow Inc. - $37B market cap, chemical giant"),
        ("DAL", "Delta Air Lines - Major airline"),
        ("DIS", "Disney - Entertainment giant"),
        ("DNA", "Ginkgo Bioworks - Biotech"),
        ("TAP", "Molson Coors - $10B market cap, beverage"),
        ("TXT", "Textron - $14B market cap, aerospace"),
        ("TPR", "Tapestry Inc. - Luxury goods"),
        ("URI", "United Rentals - $68B market cap, S&P 500"),
        ("UAL", "United Airlines - Major airline"),
        ("UPS", "United Parcel Service - Shipping giant"),
        ("SWK", "Stanley Black & Decker - $17B market cap, tools"),
        ("SYY", "Sysco - $38B market cap, food distributor"),
    ]

    # Simulate filtering with known legitimate stocks
    tickers = [ticker for ticker, _ in test_cases]
    filtered = provider._apply_basic_filters(tickers)

    # Verify all legitimate stocks are retained
    missing = set(tickers) - set(filtered)

    if missing:
        logger.error(f"❌ FAILED: {len(missing)} legitimate stocks were incorrectly filtered!")
        for ticker in missing:
            # Find description
            desc = next((d for t, d in test_cases if t == ticker), "")
            logger.error(f"  - {ticker}: {desc}")
        return False
    else:
        logger.info(f"✅ PASSED: All {len(test_cases)} legitimate stocks retained")
        return True


def test_known_etfs_are_filtered():
    """Test that known ETFs ARE filtered out."""

    provider = TickerUniverseProvider()

    # ETFs that should be filtered
    etfs_to_filter = [
        "SPY", "QQQ", "IWM", "DIA",  # Major index trackers
        "XLF", "XLE", "XLK",  # Sector ETFs
        "TQQQ", "SQQQ",  # Leveraged NASDAQ
        "UPRO", "SPXU",  # Leveraged S&P 500
        "SOXL", "SOXS",  # Leveraged semiconductors
        "TNA", "TZA",  # Leveraged Russell 2000
        "FAS", "FAZ",  # Leveraged financials
        "NUGT", "DUST",  # Leveraged gold miners
    ]

    filtered = provider._apply_basic_filters(etfs_to_filter)

    # Verify all ETFs are filtered out
    incorrectly_kept = set(filtered)

    if incorrectly_kept:
        logger.error(f"❌ FAILED: {len(incorrectly_kept)} ETFs were not filtered!")
        for ticker in incorrectly_kept:
            logger.error(f"  - {ticker}")
        return False
    else:
        logger.info(f"✅ PASSED: All {len(etfs_to_filter)} ETFs correctly filtered")
        return True


def test_filtering_statistics():
    """Test filtering with a mixed batch of tickers."""

    provider = TickerUniverseProvider()

    # Mixed batch: stocks + ETFs + invalid tickers
    mixed_tickers = [
        # Valid stocks
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "AES", "CMS", "DFS", "DHI", "URI",

        # ETFs to filter
        "SPY", "QQQ", "TQQQ", "SOXL",

        # Invalid tickers (warrants, preferred, etc.)
        "AAPL-W", "BAC$E", "MSFT123", "TOOLONG",
    ]

    logger.info(f"\n=== Testing with {len(mixed_tickers)} mixed tickers ===")
    filtered = provider._apply_basic_filters(mixed_tickers)

    # Expected: 10 valid stocks
    expected_stocks = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                      "AES", "CMS", "DFS", "DHI", "URI"}

    if set(filtered) == expected_stocks:
        logger.info(f"✅ PASSED: Correct filtering ({len(filtered)} stocks)")
        return True
    else:
        logger.error(f"❌ FAILED: Incorrect filtering")
        logger.error(f"  Expected: {expected_stocks}")
        logger.error(f"  Got: {set(filtered)}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("TICKER FILTERING VALIDATION TESTS")
    logger.info("=" * 80)

    results = []

    # Test 1: Legitimate stocks not filtered
    logger.info("\n[Test 1] Legitimate stocks should NOT be filtered")
    logger.info("-" * 80)
    results.append(("Legitimate stocks retained", test_legitimate_stocks_not_filtered()))

    # Test 2: Known ETFs are filtered
    logger.info("\n[Test 2] Known ETFs SHOULD be filtered")
    logger.info("-" * 80)
    results.append(("ETFs correctly filtered", test_known_etfs_are_filtered()))

    # Test 3: Mixed batch statistics
    logger.info("\n[Test 3] Mixed batch filtering")
    logger.info("-" * 80)
    results.append(("Mixed batch filtering", test_filtering_statistics()))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
