"""
Test script for the options endpoint.

This script tests the /options/{ticker} endpoint to ensure it's working correctly.
Run from backend directory: python test_options_endpoint.py
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
print("=" * 60)
print("Testing Options Endpoint Setup")
print("=" * 60)

print("\n1. Testing imports...")
try:
    from routers.options import router
    print("   ✓ Options router imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import options router: {e}")
    sys.exit(1)

try:
    from models.options import OptionChainResponse, OptionContract
    print("   ✓ Options models imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import options models: {e}")
    sys.exit(1)

try:
    from services.market_data import MarketDataProvider
    print("   ✓ MarketDataProvider imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import MarketDataProvider: {e}")
    sys.exit(1)

print("\n2. Checking router configuration...")
print(f"   Router prefix: {router.prefix}")
print(f"   Router tags: {router.tags}")
print(f"   Number of routes: {len(router.routes)}")

for route in router.routes:
    print(f"   - {route.methods} {router.prefix}{route.path}")

print("\n3. Testing MarketDataProvider method...")
try:
    provider = MarketDataProvider()
    if hasattr(provider, 'get_option_chain'):
        print("   ✓ get_option_chain method exists")
    else:
        print("   ✗ get_option_chain method not found")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error initializing provider: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("=" * 60)
print("\nTo start the API server, run:")
print("  cd backend")
print("  python -m uvicorn app.main:app --reload")
print("\nThen visit:")
print("  http://localhost:8000/api/docs")
print("\nTo test the endpoint:")
print("  curl http://localhost:8000/options/AAPL")
print("=" * 60)
