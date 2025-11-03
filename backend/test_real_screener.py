#!/usr/bin/env python3
"""
Test script for real Lynch Fast Growers screener with live market data.

This script tests the screener using real fundamental data from Polygon.io API.

Usage:
    python test_real_screener.py
"""

import requests
import json
from typing import Dict, Any


# API Configuration
BASE_URL = "http://localhost:8000"
SCREENER_ENDPOINT = f"{BASE_URL}/screener/lynch-fast-growers"


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def test_real_screener(params: Dict[str, Any] = None) -> None:
    """
    Test the Lynch Fast Growers screener with real data.

    Args:
        params: Optional query parameters to customize the screening
    """
    print_section("Testing Lynch Fast Growers Screener with Real Data")

    # Default parameters
    if params is None:
        params = {
            "min_earnings_growth": 15.0,
            "max_earnings_growth": 30.0,
            "max_peg_ratio": 1.0,
            "max_debt_to_equity": 0.5,
            "min_current_ratio": 1.0,
            "min_market_cap": 1.0,
            "universe": "popular",
            "limit": 10,
        }

    print("\nScreening Criteria:")
    print(f"  EPS Growth: {params['min_earnings_growth']}% - {params['max_earnings_growth']}%")
    print(f"  Max PEG Ratio: {params['max_peg_ratio']}")
    print(f"  Max Debt-to-Equity: {params['max_debt_to_equity']}")
    print(f"  Min Current Ratio: {params['min_current_ratio']}")
    print(f"  Min Market Cap: ${params['min_market_cap']}B")
    print(f"  Universe: {params['universe']}")
    print(f"  Limit: {params['limit']}")

    try:
        print("\n⏳ Fetching data from API (this may take a minute)...")

        response = requests.get(SCREENER_ENDPOINT, params=params, timeout=300)

        if response.status_code != 200:
            print(f"\n❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return

        data = response.json()

        print("\n✅ Screening Complete!")
        print(f"\nFound {data['total_results']} stocks that meet the criteria")
        print(f"Timestamp: {data['timestamp']}")

        if not data['results']:
            print("\n⚠️  No stocks passed the screening criteria.")
            print("Try relaxing the criteria (e.g., increase max_peg_ratio to 1.5)")
            return

        # Display results
        print("\n" + "-" * 80)
        print("RESULTS (Ranked by Score)")
        print("-" * 80)

        for i, stock in enumerate(data['results'], 1):
            print(f"\n{i}. {stock['ticker']} - {stock['company_name']}")
            print(f"   Sector: {stock.get('sector', 'N/A')}")
            print(f"   Score: {stock['score']:.1f}/100")
            print(f"\n   Financials:")
            print(f"   • Price: ${stock.get('price', 'N/A')}")
            print(f"   • Market Cap: ${stock.get('market_cap', 'N/A')}B")
            print(f"   • PE Ratio: {stock.get('pe_ratio', 'N/A')}")
            print(f"   • PEG Ratio: {stock.get('peg_ratio', 'N/A')}")
            print(f"   • EPS Growth: {stock.get('earnings_growth', 'N/A')}%")
            print(f"   • Revenue Growth: {stock.get('revenue_growth', 'N/A')}%")
            print(f"   • Debt-to-Equity: {stock.get('debt_to_equity', 'N/A')}")
            print(f"   • Current Ratio: {stock.get('current_ratio', 'N/A')}")

            if stock.get('reasons'):
                print(f"\n   Why it passed:")
                for reason in stock['reasons']:
                    print(f"   ✓ {reason}")

        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        avg_peg = sum(s['peg_ratio'] for s in data['results'] if s.get('peg_ratio')) / len(data['results'])
        avg_eps_growth = sum(s['earnings_growth'] for s in data['results'] if s.get('earnings_growth')) / len(data['results'])
        avg_score = sum(s['score'] for s in data['results']) / len(data['results'])

        print(f"\nAverage PEG Ratio: {avg_peg:.2f}")
        print(f"Average EPS Growth: {avg_eps_growth:.1f}%")
        print(f"Average Score: {avg_score:.1f}/100")

        # Top pick
        if data['results']:
            top_pick = data['results'][0]
            print("\n🏆 TOP PICK:")
            print(f"   {top_pick['ticker']} - {top_pick['company_name']}")
            print(f"   Score: {top_pick['score']:.1f}/100")
            print(f"   PEG: {top_pick.get('peg_ratio')}, EPS Growth: {top_pick.get('earnings_growth')}%")

    except requests.Timeout:
        print("\n❌ Request timed out. The screening process takes time to fetch")
        print("   financial data for multiple stocks. Please try again or reduce")
        print("   the universe size.")
    except requests.RequestException as e:
        print(f"\n❌ Request error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


def test_different_criteria():
    """Test with different screening criteria to show variety."""

    print_section("Test 1: Strict Criteria (Traditional Lynch)")
    test_real_screener({
        "min_earnings_growth": 15.0,
        "max_earnings_growth": 30.0,
        "max_peg_ratio": 1.0,
        "max_debt_to_equity": 0.5,
        "min_current_ratio": 1.0,
        "universe": "tech",
        "limit": 5,
    })

    input("\nPress Enter to continue to next test...")

    print_section("Test 2: Relaxed Criteria (More Results)")
    test_real_screener({
        "min_earnings_growth": 10.0,
        "max_earnings_growth": 40.0,
        "max_peg_ratio": 1.5,
        "max_debt_to_equity": 1.0,
        "min_current_ratio": 0.8,
        "universe": "popular",
        "limit": 10,
    })

    input("\nPress Enter to continue to next test...")

    print_section("Test 3: S&P 500 Sample Universe")
    test_real_screener({
        "min_earnings_growth": 15.0,
        "max_earnings_growth": 30.0,
        "max_peg_ratio": 1.0,
        "max_debt_to_equity": 0.5,
        "min_current_ratio": 1.0,
        "universe": "sp500_sample",
        "limit": 10,
    })


def main():
    """Run the tests."""
    print("\n" + "🔬" * 40)
    print("  LYNCH FAST GROWERS SCREENER - REAL DATA TEST")
    print("🔬" * 40)
    print("\nThis test uses real fundamental data from Polygon.io")
    print("Screening may take 1-2 minutes depending on API response times")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("\n❌ ERROR: Server is not responding properly")
            print("Please start the server with: uvicorn app.main:app --reload")
            return
    except requests.RequestException:
        print("\n❌ ERROR: Cannot connect to server")
        print("Please start the server with: uvicorn app.main:app --reload")
        return

    print("✅ Server is running\n")

    # Ask user which test to run
    print("Select test mode:")
    print("1. Single test with default criteria")
    print("2. Multiple tests with different criteria (interactive)")
    print("3. Quick test (tech universe, 5 results)")

    choice = input("\nEnter choice (1-3, default: 1): ").strip() or "1"

    if choice == "1":
        test_real_screener()
    elif choice == "2":
        test_different_criteria()
    elif choice == "3":
        test_real_screener({
            "min_earnings_growth": 15.0,
            "max_earnings_growth": 30.0,
            "max_peg_ratio": 1.0,
            "max_debt_to_equity": 0.5,
            "min_current_ratio": 1.0,
            "universe": "tech",
            "limit": 5,
        })
    else:
        print("Invalid choice, running default test...")
        test_real_screener()

    print("\n" + "=" * 80)
    print("🎉 Test Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("• Try different screening criteria via query parameters")
    print("• View API docs: http://localhost:8000/api/docs")
    print("• Check logs for detailed screening information")
    print("\n")


if __name__ == "__main__":
    main()
