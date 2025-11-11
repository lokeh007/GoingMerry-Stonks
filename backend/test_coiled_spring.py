#!/usr/bin/env python3
"""
Test script for The Coiled Spring screener endpoint

Tests the new volatility-based screener to ensure it works correctly.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.yfinance_provider import YFinanceProvider


def test_volatility_metrics():
    """Test volatility metrics calculation for a known ticker."""
    print("\n" + "="*80)
    print("TEST 1: Volatility Metrics Calculation")
    print("="*80)

    provider = YFinanceProvider()
    ticker = "AAPL"

    print(f"\nFetching volatility metrics for {ticker}...")

    try:
        metrics = provider.get_volatility_metrics(ticker)

        print("\n✓ Successfully fetched volatility metrics:")
        print(json.dumps(metrics, indent=2))

        # Validate expected fields
        required_fields = [
            "ticker", "has_nr7", "current_range", "avg_range_7d",
            "volatility_30d", "volatility_percentile", "is_low_volatility",
            "consolidation_score", "timestamp"
        ]

        missing_fields = [f for f in required_fields if f not in metrics]
        if missing_fields:
            print(f"\n✗ ERROR: Missing fields: {missing_fields}")
            return False

        print("\n✓ All required fields present")
        print(f"\n  NR7 Pattern: {'Yes' if metrics['has_nr7'] else 'No'}")
        print(f"  30-Day Volatility: {metrics['volatility_30d']:.2f}%" if metrics['volatility_30d'] else "  30-Day Volatility: N/A")
        print(f"  Volatility Percentile: {metrics['volatility_percentile']:.1f}%" if metrics['volatility_percentile'] else "  Volatility Percentile: N/A")
        print(f"  Low Volatility: {'Yes' if metrics['is_low_volatility'] else 'No'}")
        print(f"  Consolidation Score: {metrics['consolidation_score']:.1f}/100")

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_asset_holdings():
    """Test asset holdings data retrieval."""
    print("\n" + "="*80)
    print("TEST 2: Asset Holdings Data (Crypto/Gold)")
    print("="*80)

    provider = YFinanceProvider()

    # Test known Bitcoin holder
    ticker = "MSTR"
    print(f"\nFetching asset holdings for {ticker} (MicroStrategy - known Bitcoin holder)...")

    try:
        holdings = provider.get_asset_holdings(ticker)

        print("\n✓ Successfully fetched asset holdings:")
        print(json.dumps(holdings, indent=2))

        if holdings['has_crypto_holdings']:
            print(f"\n✓ {ticker} has crypto holdings:")
            if holdings['bitcoin_count'] > 0:
                print(f"  Bitcoin: {holdings['bitcoin_count']:,} BTC (${holdings['bitcoin_value_usd']:,})")
            if holdings['ethereum_count'] > 0:
                print(f"  Ethereum: {holdings['ethereum_count']:,} ETH (${holdings['ethereum_value_usd']:,})")

        # Test gold company
        ticker = "NEM"
        print(f"\nFetching asset holdings for {ticker} (Newmont - gold mining)...")
        holdings = provider.get_asset_holdings(ticker)

        if holdings['has_gold_holdings']:
            print(f"\n✓ {ticker} has gold holdings:")
            print(f"  Gold: {holdings['gold_oz']:,} oz (${holdings['gold_value_usd']:,})")

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_consolidation_scoring():
    """Test consolidation score calculation."""
    print("\n" + "="*80)
    print("TEST 3: Consolidation Score Calculation")
    print("="*80)

    provider = YFinanceProvider()

    # Test multiple tickers with different characteristics
    test_tickers = ["AAPL", "MSFT", "GOOGL"]

    print(f"\nTesting consolidation scoring for {len(test_tickers)} tickers...")

    try:
        scores = []
        for ticker in test_tickers:
            metrics = provider.get_volatility_metrics(ticker)
            scores.append({
                "ticker": ticker,
                "score": metrics['consolidation_score'],
                "nr7": metrics['has_nr7'],
                "volatility": metrics['volatility_30d'],
                "percentile": metrics['volatility_percentile']
            })

        print("\n✓ Consolidation scores calculated:")
        print("\n  Ticker | Score | NR7 | Volatility | Percentile")
        print("  " + "-" * 55)
        for s in sorted(scores, key=lambda x: x['score'], reverse=True):
            nr7_str = "Yes" if s['nr7'] else "No"
            vol_str = f"{s['volatility']:.1f}%" if s['volatility'] else "N/A"
            pct_str = f"{s['percentile']:.0f}%" if s['percentile'] else "N/A"
            print(f"  {s['ticker']:6} | {s['score']:5.1f} | {nr7_str:3} | {vol_str:10} | {pct_str}")

        print("\n✓ Score ranges from 0-100:")
        print(f"  Highest: {max(s['score'] for s in scores):.1f}")
        print(f"  Lowest: {min(s['score'] for s in scores):.1f}")

        # Validate scores are in range
        for s in scores:
            if not (0 <= s['score'] <= 100):
                print(f"\n✗ ERROR: Score out of range for {s['ticker']}: {s['score']}")
                return False

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COILED SPRING SCREENER - TEST SUITE")
    print("="*80)

    results = []

    # Test 1: Volatility metrics
    results.append(("Volatility Metrics", test_volatility_metrics()))

    # Test 2: Asset holdings
    results.append(("Asset Holdings", test_asset_holdings()))

    # Test 3: Consolidation scoring
    results.append(("Consolidation Scoring", test_consolidation_scoring()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
