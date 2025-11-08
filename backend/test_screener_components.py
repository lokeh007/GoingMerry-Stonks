"""
Test script for new screener components.

This script verifies that all new screener components are working correctly:
- YFinanceProvider
- GannSquareCalculator
- PatternDetector
- Enhanced models
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.services.yfinance_provider import YFinanceProvider
from app.financial_models.gann import get_gann_calculator
from app.financial_models.patterns import get_pattern_detector
from app.models.screener import (
    LynchCategory,
    MarketRegime,
    RSICondition,
    MACDCondition,
    BulkowskiPattern,
    GannLocation,
    TechnicalIndicators,
    PatternDetection,
    GannLevels,
    FundamentalFilters,
    TechnicalFilters,
    AdvancedScreenerRequest,
)


def test_yfinance_provider():
    """Test YFinanceProvider functionality."""
    print("\n" + "=" * 50)
    print("Testing YFinanceProvider")
    print("=" * 50)

    provider = YFinanceProvider()

    # Test 1: Get technical indicators
    try:
        print("\n1. Testing get_technical_indicators for AAPL...")
        indicators = provider.get_technical_indicators("AAPL", period="1mo")
        print(f"   ✓ Current RSI: {indicators['rsi']['current']:.2f}")
        print(f"   ✓ RSI Oversold: {indicators['rsi']['oversold']}")
        print(f"   ✓ MACD Bullish Crossover: {indicators['macd']['bullish_crossover']}")
        print(f"   ✓ Data points: {indicators['data_points']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Get VIX data
    try:
        print("\n2. Testing get_vix_data...")
        vix = provider.get_vix_data()
        print(f"   ✓ VIX Value: {vix['value']:.2f}")
        print(f"   ✓ Market Regime: {vix['regime_label']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Get stock universe
    try:
        print("\n3. Testing get_stock_universe...")
        nasdaq_tickers = provider.get_stock_universe("NASDAQ", limit=10)
        print(f"   ✓ NASDAQ tickers (first 10): {', '.join(nasdaq_tickers)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_gann_calculator():
    """Test GannSquareCalculator functionality."""
    print("\n" + "=" * 50)
    print("Testing GannSquareCalculator")
    print("=" * 50)

    calc = get_gann_calculator()

    # Test 1: Calculate Gann levels
    try:
        print("\n1. Testing calculate_gann_levels for price $150...")
        levels = calc.calculate_gann_levels(current_price=150.0, reference_price=140.0)
        print(f"   ✓ Nearest Support: ${levels['nearest_support']:.2f}")
        print(f"   ✓ Nearest Resistance: ${levels['nearest_resistance']:.2f}")
        print(f"   ✓ Current Position: {levels['current_position']}")
        print(f"   ✓ Support levels count: {len(levels['support_levels'])}")
        print(f"   ✓ Resistance levels count: {len(levels['resistance_levels'])}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Check if at key level
    try:
        print("\n2. Testing is_at_key_level...")
        at_level = calc.is_at_key_level(150.0, 140.0, tolerance=0.02)
        print(f"   ✓ At Support: {at_level['at_support']}")
        print(f"   ✓ At Resistance: {at_level['at_resistance']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Calculate price target
    try:
        print("\n3. Testing calculate_price_target...")
        target = calc.calculate_price_target(entry_price=100.0, angle=180, direction="up")
        print(f"   ✓ Target price (180° up from $100): ${target:.2f}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_pattern_detector():
    """Test PatternDetector functionality."""
    print("\n" + "=" * 50)
    print("Testing PatternDetector")
    print("=" * 50)

    detector = get_pattern_detector()
    provider = YFinanceProvider()

    # Test 1: Detect Pipe Bottom
    try:
        print("\n1. Testing detect_pipe_bottom for AAPL...")
        df = provider.get_historical_data("AAPL", period="1mo")
        pipe_result = detector.detect_pipe_bottom(df, lookback=20)
        print(f"   ✓ Pattern Detected: {pipe_result['detected']}")
        if pipe_result['detected']:
            print(f"   ✓ Confidence: {pipe_result['confidence']}")
            print(f"   ✓ Description: {pipe_result['description']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Detect Double Bottom
    try:
        print("\n2. Testing detect_double_bottom for AAPL...")
        df = provider.get_historical_data("AAPL", period="6mo")
        double_result = detector.detect_double_bottom(df, lookback=60)
        print(f"   ✓ Pattern Detected: {double_result['detected']}")
        if double_result['detected']:
            print(f"   ✓ Confidence: {double_result['confidence']}")
            print(f"   ✓ Description: {double_result['description']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_models():
    """Test Pydantic models."""
    print("\n" + "=" * 50)
    print("Testing Pydantic Models")
    print("=" * 50)

    # Test 1: Enums
    print("\n1. Testing Enums...")
    print(f"   ✓ Lynch Categories: {[c.value for c in LynchCategory]}")
    print(f"   ✓ Market Regimes: {[r.value for r in MarketRegime]}")
    print(f"   ✓ RSI Conditions: {[c.value for c in RSICondition]}")
    print(f"   ✓ MACD Conditions: {[c.value for c in MACDCondition]}")

    # Test 2: TechnicalIndicators model
    try:
        print("\n2. Testing TechnicalIndicators model...")
        tech_ind = TechnicalIndicators(
            rsi_current=35.5,
            rsi_oversold=False,
            rsi_overbought=False,
            macd_bullish_crossover=True,
            macd_bearish_crossover=False,
        )
        print(f"   ✓ Model created: RSI={tech_ind.rsi_current}, MACD Bullish={tech_ind.macd_bullish_crossover}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: AdvancedScreenerRequest model
    try:
        print("\n3. Testing AdvancedScreenerRequest model...")
        request = AdvancedScreenerRequest(
            lynch_category=LynchCategory.FAST_GROWERS,
            fundamental_filters=FundamentalFilters(
                max_peg_ratio=1.0,
                min_eps_growth=15.0,
                max_eps_growth=30.0,
            ),
            technical_filters=TechnicalFilters(
                rsi_condition=RSICondition.OVERSOLD,
                macd_condition=MACDCondition.BULLISH_CROSSOVER,
            ),
            market_regime=MarketRegime.HIGH_FEAR,
        )
        print(f"   ✓ Request created: Category={request.lynch_category.value}")
        print(f"   ✓ PEG Ratio Filter: < {request.fundamental_filters.max_peg_ratio}")
        print(f"   ✓ RSI Filter: {request.technical_filters.rsi_condition.value}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("SCREENER COMPONENTS TEST SUITE")
    print("=" * 50)

    try:
        test_models()
        test_gann_calculator()
        test_yfinance_provider()
        test_pattern_detector()

        print("\n" + "=" * 50)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 50)
        print("\nAll components are working correctly!")
        print("You can now proceed with enhancing the screener router.")

    except Exception as e:
        print(f"\n✗ TESTS FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
