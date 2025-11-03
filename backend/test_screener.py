#!/usr/bin/env python3
"""
Test script for Alpha Engine screener endpoints.

This script tests the screener API endpoints to verify they work correctly.
Run this after starting the FastAPI server.

Usage:
    python test_screener.py
"""

import requests
from typing import Dict, Any
import json


# API Configuration
BASE_URL = "http://localhost:8000"
SCREENER_ENDPOINT = f"{BASE_URL}/screener/lynch-fast-growers"
LIST_ENDPOINT = f"{BASE_URL}/screener/screeners"


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_result(success: bool, message: str) -> None:
    """Print a test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")


def test_list_screeners() -> bool:
    """Test the list screeners endpoint."""
    print_section("Test 1: List Available Screeners")

    try:
        response = requests.get(LIST_ENDPOINT)

        if response.status_code != 200:
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False

        data = response.json()

        # Verify response structure
        required_fields = ['total_screeners', 'screeners', 'alpha_engine_version']
        for field in required_fields:
            if field not in data:
                print_result(False, f"Missing field: {field}")
                return False

        print_result(True, f"Found {data['total_screeners']} available screeners")
        print(f"\nAvailable screeners:")
        for screener in data['screeners']:
            status = screener.get('status', 'active')
            print(f"  - {screener['name']} ({status})")

        return True

    except requests.RequestException as e:
        print_result(False, f"Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print_result(False, f"JSON decode error: {e}")
        return False


def test_lynch_screener_default() -> bool:
    """Test Lynch Fast Growers screener with default parameters."""
    print_section("Test 2: Lynch Fast Growers - Default Parameters")

    try:
        response = requests.get(SCREENER_ENDPOINT)

        if response.status_code != 200:
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False

        data = response.json()

        # Verify response structure
        required_fields = ['screener_name', 'description', 'total_results', 'results', 'timestamp', 'criteria']
        for field in required_fields:
            if field not in data:
                print_result(False, f"Missing field: {field}")
                return False

        print_result(True, f"Received {data['total_results']} results")

        # Display first result
        if data['results']:
            stock = data['results'][0]
            print(f"\nTop Result:")
            print(f"  Ticker: {stock['ticker']}")
            print(f"  Company: {stock['company_name']}")
            print(f"  Sector: {stock.get('sector', 'N/A')}")
            print(f"  Score: {stock['score']}")
            print(f"  PEG Ratio: {stock.get('peg_ratio', 'N/A')}")
            print(f"  Earnings Growth: {stock.get('earnings_growth', 'N/A')}%")
            print(f"  Reasons: {', '.join(stock['reasons'][:2])}...")

        # Verify criteria
        criteria = data['criteria']
        print(f"\nCriteria Used:")
        print(f"  Min Earnings Growth: {criteria.get('min_earnings_growth')}%")
        print(f"  Max PEG Ratio: {criteria.get('max_peg_ratio')}")
        print(f"  Min Current Ratio: {criteria.get('min_current_ratio')}")
        print(f"  Max Debt-to-Equity: {criteria.get('max_debt_to_equity')}")
        print(f"  Min Market Cap: ${criteria.get('min_market_cap')}B")

        return True

    except requests.RequestException as e:
        print_result(False, f"Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print_result(False, f"JSON decode error: {e}")
        return False


def test_lynch_screener_custom() -> bool:
    """Test Lynch Fast Growers screener with custom parameters."""
    print_section("Test 3: Lynch Fast Growers - Custom Parameters")

    params = {
        'min_earnings_growth': 15.0,
        'max_peg_ratio': 2.0,
        'min_current_ratio': 1.5,
        'max_debt_to_equity': 1.0,
        'min_market_cap': 5.0,
        'limit': 10
    }

    try:
        response = requests.get(SCREENER_ENDPOINT, params=params)

        if response.status_code != 200:
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False

        data = response.json()

        print_result(True, f"Received {data['total_results']} results with custom params")

        # Verify custom parameters were applied
        criteria = data['criteria']
        params_match = all([
            criteria.get('min_earnings_growth') == params['min_earnings_growth'],
            criteria.get('max_peg_ratio') == params['max_peg_ratio'],
            criteria.get('min_current_ratio') == params['min_current_ratio'],
            criteria.get('max_debt_to_equity') == params['max_debt_to_equity'],
            criteria.get('min_market_cap') == params['min_market_cap'],
        ])

        if not params_match:
            print_result(False, "Custom parameters not applied correctly")
            return False

        print_result(True, "Custom parameters applied correctly")

        # Verify limit was respected
        if len(data['results']) > params['limit']:
            print_result(False, f"Result limit exceeded: {len(data['results'])} > {params['limit']}")
            return False

        print_result(True, f"Result limit respected: {len(data['results'])} <= {params['limit']}")

        return True

    except requests.RequestException as e:
        print_result(False, f"Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print_result(False, f"JSON decode error: {e}")
        return False


def test_stock_result_structure() -> bool:
    """Test that stock results have all required fields."""
    print_section("Test 4: Stock Result Data Structure")

    try:
        response = requests.get(SCREENER_ENDPOINT, params={'limit': 1})
        data = response.json()

        if not data['results']:
            print_result(False, "No results to test")
            return False

        stock = data['results'][0]

        # Required fields
        required_fields = {
            'ticker': str,
            'company_name': str,
            'score': (int, float),
            'reasons': list,
        }

        # Optional fields (should be present in placeholder data)
        optional_fields = {
            'sector': str,
            'market_cap': (int, float),
            'price': (int, float),
            'pe_ratio': (int, float),
            'peg_ratio': (int, float),
            'revenue_growth': (int, float),
            'earnings_growth': (int, float),
            'debt_to_equity': (int, float),
            'current_ratio': (int, float),
        }

        all_passed = True

        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in stock:
                print_result(False, f"Missing required field: {field}")
                all_passed = False
            elif not isinstance(stock[field], expected_type):
                print_result(False, f"Field {field} has wrong type: {type(stock[field])}")
                all_passed = False
            else:
                print_result(True, f"Required field '{field}' present and valid")

        # Check optional fields
        for field, expected_type in optional_fields.items():
            if field in stock and stock[field] is not None:
                if not isinstance(stock[field], expected_type):
                    print_result(False, f"Field {field} has wrong type: {type(stock[field])}")
                    all_passed = False
                else:
                    print_result(True, f"Optional field '{field}' present and valid")

        # Verify score is in valid range
        if not (0 <= stock['score'] <= 100):
            print_result(False, f"Score out of range: {stock['score']}")
            all_passed = False
        else:
            print_result(True, f"Score in valid range (0-100): {stock['score']}")

        return all_passed

    except requests.RequestException as e:
        print_result(False, f"Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print_result(False, f"JSON decode error: {e}")
        return False


def test_parameter_validation() -> bool:
    """Test parameter validation with invalid inputs."""
    print_section("Test 5: Parameter Validation")

    test_cases = [
        {
            'name': 'Negative earnings growth',
            'params': {'min_earnings_growth': -10},
            'should_fail': True
        },
        {
            'name': 'Excessive PEG ratio',
            'params': {'max_peg_ratio': 100},
            'should_fail': True
        },
        {
            'name': 'Zero limit',
            'params': {'limit': 0},
            'should_fail': True
        },
        {
            'name': 'Excessive limit',
            'params': {'limit': 1000},
            'should_fail': True
        },
        {
            'name': 'Valid edge case',
            'params': {'min_earnings_growth': 0, 'max_peg_ratio': 10, 'limit': 1},
            'should_fail': False
        },
    ]

    all_passed = True

    for case in test_cases:
        try:
            response = requests.get(SCREENER_ENDPOINT, params=case['params'])

            if case['should_fail']:
                if response.status_code == 200:
                    print_result(False, f"{case['name']}: Should have failed validation")
                    all_passed = False
                else:
                    print_result(True, f"{case['name']}: Correctly rejected (status {response.status_code})")
            else:
                if response.status_code != 200:
                    print_result(False, f"{case['name']}: Should have succeeded (status {response.status_code})")
                    all_passed = False
                else:
                    print_result(True, f"{case['name']}: Correctly accepted")

        except requests.RequestException as e:
            print_result(False, f"{case['name']}: Request error: {e}")
            all_passed = False

    return all_passed


def main() -> None:
    """Run all tests."""
    print("\n" + "🔬" * 35)
    print("  ALPHA ENGINE SCREENER API TESTS")
    print("🔬" * 35)
    print(f"\nTesting API at: {BASE_URL}")
    print("Make sure the FastAPI server is running!")

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

    # Run tests
    tests = [
        test_list_screeners,
        test_lynch_screener_default,
        test_lynch_screener_custom,
        test_stock_result_structure,
        test_parameter_validation,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_result(False, f"Unexpected error: {e}")
            results.append(False)

    # Summary
    print_section("Test Summary")
    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! Alpha Engine is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
