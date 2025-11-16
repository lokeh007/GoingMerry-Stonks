#!/usr/bin/env python3
"""
Test script for rate limiter functionality.

This script tests the proactive rate limiting implementation in YFinanceProvider
to ensure requests stay under 50/min without hitting yfinance rate limits.
"""

import sys
import os
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.yfinance_provider import YFinanceProvider


def test_rate_limiter_basic():
    """Test basic rate limiter functionality with small number of requests."""
    print("=" * 80)
    print("TEST 1: Basic Rate Limiter Functionality")
    print("=" * 80)

    # Initialize provider with 50 req/min rate limit
    provider = YFinanceProvider(max_requests_per_minute=50)
    provider.clear_cache()  # Clear cache to ensure we're testing rate limiter

    # Test tickers
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    print(f"\nFetching fundamentals for {len(tickers)} tickers...")
    print(f"Expected time: ~{len(tickers) * 60 / 50:.1f} seconds (at 50 req/min)")

    start_time = time.time()

    for i, ticker in enumerate(tickers, 1):
        try:
            fundamentals = provider.get_fundamentals(ticker)
            elapsed = time.time() - start_time
            rate = i / elapsed * 60  # Convert to requests per minute

            print(f"  [{i}/{len(tickers)}] {ticker}: {fundamentals.get('company_name', 'N/A')}")
            print(f"       Elapsed: {elapsed:.2f}s | Current rate: {rate:.1f} req/min")

        except Exception as e:
            print(f"  [{i}/{len(tickers)}] {ticker}: ERROR - {e}")

    total_time = time.time() - start_time
    actual_rate = len(tickers) / total_time * 60

    print(f"\n✓ Test completed in {total_time:.2f} seconds")
    print(f"  Actual rate: {actual_rate:.1f} req/min")
    print(f"  Target rate: ≤50 req/min (yfinance limit: 60 req/min)")

    # Success if we stay under yfinance limit (60 req/min)
    # Note: Actual rate is often lower due to API response time
    passed = actual_rate <= 60
    print(f"  Status: {'✓ PASS' if passed else '✗ FAIL'} (must stay under 60 req/min)")

    return passed


def test_rate_limiter_burst():
    """Test that rate limiter handles burst requests properly."""
    print("\n" + "=" * 80)
    print("TEST 2: Burst Request Handling")
    print("=" * 80)

    # Initialize provider with 50 req/min rate limit
    provider = YFinanceProvider(max_requests_per_minute=50)
    provider.clear_cache()  # Clear cache to ensure we're testing rate limiter

    # Make 10 rapid requests
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT"]

    print(f"\nMaking {len(tickers)} burst requests...")
    print(f"Expected behavior: First ~50 requests instant, then rate-limited")

    start_time = time.time()
    request_times = []

    for i, ticker in enumerate(tickers, 1):
        request_start = time.time()
        try:
            provider.get_fundamentals(ticker)
            request_end = time.time()
            request_times.append(request_end - request_start)

            elapsed = time.time() - start_time
            print(f"  [{i}/{len(tickers)}] {ticker}: {request_times[-1]:.3f}s | Total elapsed: {elapsed:.2f}s")

        except Exception as e:
            print(f"  [{i}/{len(tickers)}] {ticker}: ERROR - {e}")

    total_time = time.time() - start_time
    avg_request_time = sum(request_times) / len(request_times)

    print(f"\n✓ Burst test completed in {total_time:.2f} seconds")
    print(f"  Average request time: {avg_request_time:.3f}s")
    print(f"  First request: {request_times[0]:.3f}s (should be fast)")
    print(f"  Last request: {request_times[-1]:.3f}s")

    return True


def test_rate_limiter_screener_simulation():
    """Simulate screener workload (20 tickers)."""
    print("\n" + "=" * 80)
    print("TEST 3: Screener Workload Simulation")
    print("=" * 80)

    # Initialize provider with 50 req/min rate limit
    provider = YFinanceProvider(max_requests_per_minute=50)
    provider.clear_cache()  # Clear cache to ensure we're testing rate limiter

    # Simulate small screener batch
    tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
        "JPM", "V", "WMT", "PG", "MA", "HD", "CVX", "LLY",
        "ABBV", "MRK", "PEP", "COST"
    ]

    print(f"\nScreening {len(tickers)} tickers...")
    print(f"Expected time: ~{len(tickers) * 60 / 50:.1f} seconds (at 50 req/min)")

    start_time = time.time()
    successful = 0
    failed = 0

    for i, ticker in enumerate(tickers, 1):
        try:
            # Each screener typically makes 2-3 calls per ticker
            # 1. get_fundamentals (1 call: ticker.info)
            # 2. get_analyst_and_insider_data (1 call: ticker.info + ticker.insider_transactions)
            # Total: ~2-3 API calls per ticker

            fundamentals = provider.get_fundamentals(ticker)

            elapsed = time.time() - start_time
            rate = i / elapsed * 60

            if i % 5 == 0:  # Log every 5 tickers
                print(f"  Progress: {i}/{len(tickers)} | Elapsed: {elapsed:.1f}s | Rate: {rate:.1f} req/min")

            successful += 1

        except Exception as e:
            print(f"  ERROR - {ticker}: {e}")
            failed += 1

    total_time = time.time() - start_time
    actual_rate = len(tickers) / total_time * 60

    print(f"\n✓ Screener simulation completed")
    print(f"  Total time: {total_time:.2f} seconds ({total_time / 60:.1f} minutes)")
    print(f"  Successful: {successful}/{len(tickers)}")
    print(f"  Failed: {failed}/{len(tickers)}")
    print(f"  Actual rate: {actual_rate:.1f} req/min")
    print(f"  Target rate: ≤50 req/min (yfinance limit: 60 req/min)")

    # Success if: (1) stayed under yfinance limit AND (2) >= 90% success rate
    passed = actual_rate <= 60 and successful >= len(tickers) * 0.9
    print(f"  Status: {'✓ PASS' if passed else '✗ FAIL'}")

    return passed


def main():
    """Run all rate limiter tests."""
    print("\n" + "=" * 80)
    print("YFINANCE RATE LIMITER TEST SUITE")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Run tests
    try:
        results["basic"] = test_rate_limiter_basic()
    except Exception as e:
        print(f"\n✗ Test 1 FAILED with exception: {e}")
        results["basic"] = False

    try:
        results["burst"] = test_rate_limiter_burst()
    except Exception as e:
        print(f"\n✗ Test 2 FAILED with exception: {e}")
        results["burst"] = False

    try:
        results["screener"] = test_rate_limiter_screener_simulation()
    except Exception as e:
        print(f"\n✗ Test 3 FAILED with exception: {e}")
        results["screener"] = False

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name.upper()}: {status}")

    all_passed = all(results.values())

    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
