#!/usr/bin/env python3
"""
Standalone test for ticker filtering logic (no dependencies).

Tests the ETF filtering improvements without requiring full app imports.
"""

import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_comprehensive_etf_list():
    """Comprehensive ETF whitelist (copied from ticker_universe.py)."""
    return {
        # ===== Major Index Trackers =====
        "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "VEA", "VWO", "EEM", "AGG",
        "BND", "LQD", "HYG", "TLT", "IEF", "SHY", "MUB", "EMB", "IEMG", "IEFA",
        "GLD", "SLV", "VNQ", "VIG", "VYM", "SCHD", "RSP", "MDY", "IJR", "IJH",

        # ===== Sector SPDR ETFs (XL-) =====
        "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE",
        "XLC", "XTL", "XTN", "XPH", "XHS", "XES", "XAR", "XME", "XHB", "XRT",

        # ===== Vanguard Sector ETFs (VXX) =====
        "VGT", "VHT", "VDC", "VCR", "VIS", "VDE", "VAW", "VFH", "VPU", "VOX",

        # ===== iShares Core ETFs =====
        "IVV", "IEMG", "IEFA", "IJH", "IJR", "IWF", "IWD", "IWM", "IWN", "IWO",
        "IWP", "IWR", "IWS", "IWV",

        # ===== Commodity/Currency ETFs =====
        "GLD", "SLV", "USO", "UNG", "DBA", "DBC", "UUP", "FXE", "FXY", "FXB",
        "DBO", "DBB", "PPLT", "PALL", "GLTR", "GSG", "DJP", "USCI", "PDBC",

        # ===== Volatility ETFs =====
        "VXX", "UVXY", "SVXY", "VIXY", "VIXM", "ZIV",

        # ===== Leveraged/Inverse ETFs =====
        "SOXL", "SOXS", "TECL", "TECS", "FAS", "FAZ", "TNA", "TZA",
        "ERX", "ERY", "CURE", "RXD", "DIG", "DUG", "DDM", "DXD",
        "SSO", "SDS", "UPRO", "SPXU", "TQQQ", "SQQQ", "NUGT", "DUST",
        "JNUG", "JDST", "UGAZ", "DGAZ",
    }


def apply_basic_filters(tickers):
    """Simplified version of _apply_basic_filters for testing."""
    known_etfs = get_comprehensive_etf_list()
    filtered = []

    for ticker in tickers:
        ticker = ticker.strip().upper()

        # Skip empty
        if not ticker:
            continue

        # Skip indexes
        if ticker.startswith("^"):
            continue

        # Skip very long tickers (warrants/units)
        if len(ticker) > 5:
            continue

        # Skip special characters
        if any(char in ticker for char in ["$", "-", ".", "/", "~", " "]):
            continue

        # Skip tickers with numbers
        if any(char.isdigit() for char in ticker):
            continue

        # Skip known ETFs
        if ticker in known_etfs:
            continue

        # Skip test symbols
        if ticker in ["TEST", "SAMPLE", "ZVZZT"]:
            continue

        filtered.append(ticker)

    return filtered


def test_legitimate_stocks_not_filtered():
    """Test that legitimate stocks are NOT filtered out."""

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

    tickers = [ticker for ticker, _ in test_cases]
    filtered = apply_basic_filters(tickers)

    missing = set(tickers) - set(filtered)

    if missing:
        logger.error(f"❌ FAILED: {len(missing)} legitimate stocks were incorrectly filtered!")
        for ticker in missing:
            desc = next((d for t, d in test_cases if t == ticker), "")
            logger.error(f"  - {ticker}: {desc}")
        return False
    else:
        logger.info(f"✅ PASSED: All {len(test_cases)} legitimate stocks retained")
        logger.info(f"   Tested: {', '.join(sorted(tickers))}")
        return True


def test_known_etfs_are_filtered():
    """Test that known ETFs ARE filtered out."""

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

    filtered = apply_basic_filters(etfs_to_filter)

    incorrectly_kept = set(filtered)

    if incorrectly_kept:
        logger.error(f"❌ FAILED: {len(incorrectly_kept)} ETFs were not filtered!")
        for ticker in incorrectly_kept:
            logger.error(f"  - {ticker}")
        return False
    else:
        logger.info(f"✅ PASSED: All {len(etfs_to_filter)} ETFs correctly filtered")
        logger.info(f"   Filtered: {', '.join(sorted(etfs_to_filter))}")
        return True


def test_mixed_batch():
    """Test filtering with a mixed batch of tickers."""

    mixed_tickers = [
        # Valid stocks
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "AES", "CMS", "DFS", "DHI", "URI",

        # ETFs to filter
        "SPY", "QQQ", "TQQQ", "SOXL",

        # Invalid tickers
        "AAPL-W", "BAC$E", "MSFT123", "TOOLONG",
    ]

    filtered = apply_basic_filters(mixed_tickers)

    expected_stocks = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                      "AES", "CMS", "DFS", "DHI", "URI"}

    if set(filtered) == expected_stocks:
        logger.info(f"✅ PASSED: Correct filtering ({len(filtered)}/{len(mixed_tickers)} stocks)")
        logger.info(f"   Kept: {', '.join(sorted(filtered))}")
        return True
    else:
        logger.error(f"❌ FAILED: Incorrect filtering")
        logger.error(f"  Expected: {expected_stocks}")
        logger.error(f"  Got: {set(filtered)}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("TICKER FILTERING VALIDATION TESTS (Standalone)")
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

    # Test 3: Mixed batch
    logger.info("\n[Test 3] Mixed batch filtering")
    logger.info("-" * 80)
    results.append(("Mixed batch filtering", test_mixed_batch()))

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
        logger.info("\nIMPROVEMENTS VALIDATED:")
        logger.info("  ✅ No false positives (legitimate stocks kept)")
        logger.info("  ✅ No false negatives (ETFs filtered)")
        logger.info("  ✅ Whitelist approach is working correctly")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
