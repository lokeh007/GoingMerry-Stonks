"""
Quick test script to verify Polygon API connection.
Run this from the backend directory: python test_api.py
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv
from services.market_data import MarketDataProvider, MarketDataError

# Load environment variables
load_dotenv()

def test_api_connection():
    """Test the Polygon API connection with a simple stock quote request."""
    print("=" * 60)
    print("Testing Polygon.io API Connection")
    print("=" * 60)

    try:
        # Initialize provider
        print("\n1. Initializing MarketDataProvider...")
        provider = MarketDataProvider()
        print("   ✓ Provider initialized successfully")

        # Test health check
        print("\n2. Testing API health check...")
        is_healthy = provider.health_check()
        if is_healthy:
            print("   ✓ API connection is healthy")
        else:
            print("   ✗ API health check failed")
            return

        # Test getting a stock quote
        print("\n3. Fetching stock quote for AAPL...")
        quote = provider.get_stock_quote("AAPL")

        print("\n" + "=" * 60)
        print("SUCCESS! API Connection Working")
        print("=" * 60)
        print(f"\nAAPL Stock Quote:")
        print(f"  Price:           ${quote['price']:.2f}")
        print(f"  Change:          ${quote['change']:.2f} ({quote['change_percent']:.2f}%)")
        print(f"  Previous Close:  ${quote['previous_close']:.2f}")
        print(f"  Day High:        ${quote['day_high']:.2f}")
        print(f"  Day Low:         ${quote['day_low']:.2f}")
        print(f"  Day Open:        ${quote['day_open']:.2f}")
        print(f"  Volume:          {quote['volume']:,}")
        print(f"  Timestamp:       {quote['timestamp']}")
        print("\n" + "=" * 60)

    except MarketDataError as e:
        print(f"\n✗ Market Data Error: {e}")
        print("\nPlease check:")
        print("  1. Your API key is correct in backend/.env")
        print("  2. You have an active Polygon.io subscription")
        print("  3. Your internet connection is working")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)
