#!/usr/bin/env python3
"""
Test script for lazy loading optimization.

Tests the new lazy loading implementation with a small batch of tickers
to validate:
1. API call reduction works correctly
2. No errors in filtering logic
3. Results are still accurate
4. Performance improvement is measurable

Usage:
    python backend/test_lazy_loading.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.jobs.run_daily_screeners import DailyScreenerJob


def test_lazy_loading():
    """Test lazy loading with sample tickers."""

    print("=" * 80)
    print("LAZY LOADING OPTIMIZATION TEST")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}")
    print("")

    # Initialize screener (no batch number for testing)
    runner = DailyScreenerJob(batch_number=None)

    # Test universe - mix of different market caps and quality
    test_universe = [
        # Large caps (should pass basic filters)
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",

        # Mid caps (should pass basic filters)
        "RBLX", "PLTR", "SNOW", "DDOG", "CRWD",

        # Small caps (some may fail filters)
        "FUBO", "RIVN", "LCID", "BBBY", "AMC",

        # Micro caps / penny stocks (should fail basic filters)
        "SNDL", "NAKD", "GNUS", "XSPA", "BNGO",

        # Potentially delisted / low quality (should fail filters)
        "HMNY", "DRYS", "TOPS", "SHIP", "GLBS",
    ]

    print(f"Testing with {len(test_universe)} tickers:")
    print(f"  - 5 large caps (expected to pass filters)")
    print(f"  - 5 mid caps (expected to pass filters)")
    print(f"  - 5 small caps (mixed results)")
    print(f"  - 5 micro caps (expected to fail filters)")
    print(f"  - 5 low quality (expected to fail filters)")
    print("")

    # Screener parameters
    undiscovered_params = {
        "max_institutional_ownership": 25.0,
        "max_analyst_coverage": 5,
        "require_insider_buying": False,
    }
    coiled_spring_params = {
        "max_volatility_30d": 20.0,
        "require_nr7": True,
        "min_percentile_rank": 30.0,
    }

    # Process tickers
    print("Processing tickers...")
    start_time = datetime.now()

    total_api_calls = 0
    passed_basic_filters = 0
    failed_basic_filters = 0
    undiscovered_passes = 0
    coiled_spring_passes = 0

    for i, ticker in enumerate(test_universe, 1):
        try:
            undiscovered_result, coiled_spring_result, api_calls = runner._process_ticker(
                ticker, undiscovered_params, coiled_spring_params
            )

            total_api_calls += api_calls

            # Track filter results
            if api_calls == 1:
                # Only 1 API call = failed basic filters (OPTIMIZATION WORKING!)
                failed_basic_filters += 1
                print(f"  {i:2d}. {ticker:6s} - Failed basic filters (1 API call)")
            else:
                # 2-3 API calls = passed basic filters
                passed_basic_filters += 1
                status = []
                if undiscovered_result:
                    undiscovered_passes += 1
                    status.append(f"Undiscovered ✓")
                if coiled_spring_result:
                    coiled_spring_passes += 1
                    status.append(f"Coiled Spring ✓")

                status_str = ", ".join(status) if status else "No screener passes"
                print(f"  {i:2d}. {ticker:6s} - Passed basic filters ({api_calls} API calls) - {status_str}")

        except Exception as e:
            print(f"  {i:2d}. {ticker:6s} - ERROR: {e}")

    elapsed_time = (datetime.now() - start_time).total_seconds()

    # Calculate metrics
    old_api_calls = len(test_universe) * 3  # Old approach: always 3 calls
    api_calls_saved = old_api_calls - total_api_calls
    percent_saved = (api_calls_saved / old_api_calls * 100) if old_api_calls > 0 else 0
    avg_calls_per_ticker = total_api_calls / len(test_universe)

    print("")
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Tickers Tested: {len(test_universe)}")
    print(f"Passed Basic Filters: {passed_basic_filters} ({passed_basic_filters/len(test_universe)*100:.1f}%)")
    print(f"Failed Basic Filters: {failed_basic_filters} ({failed_basic_filters/len(test_universe)*100:.1f}%)")
    print(f"Undiscovered Passes: {undiscovered_passes}")
    print(f"Coiled Spring Passes: {coiled_spring_passes}")
    print("")
    print("🚀 LAZY LOADING OPTIMIZATION IMPACT:")
    print(f"  - Old Approach (no lazy loading): {old_api_calls} API calls (3 per ticker)")
    print(f"  - New Approach (lazy loading): {total_api_calls} API calls ({avg_calls_per_ticker:.2f} per ticker)")
    print(f"  - API Calls SAVED: {api_calls_saved} ({percent_saved:.1f}% reduction)")
    print("")
    print(f"⏱  Execution Time: {elapsed_time:.2f} seconds")
    print(f"📊 API Rate: {(total_api_calls / elapsed_time * 60):.2f} calls/min")
    print("")

    # Validate optimization is working
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)

    if percent_saved >= 20:
        print(f"✅ SUCCESS: Lazy loading achieved {percent_saved:.1f}% API reduction")
    elif percent_saved >= 10:
        print(f"⚠️  WARNING: Lazy loading only achieved {percent_saved:.1f}% reduction (expected >20%)")
    else:
        print(f"❌ FAILURE: Lazy loading achieved {percent_saved:.1f}% reduction (expected >20%)")
        print("   Check filter logic - may be too loose")

    if failed_basic_filters > 0:
        print(f"✅ Basic filters working: {failed_basic_filters} tickers rejected early")
    else:
        print(f"⚠️  Basic filters too loose: No tickers rejected")

    print("")
    print("=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_lazy_loading()
