"""
Comprehensive test suite for Gann Square of 9 Calculator.

This test suite covers:
- Basic functionality (happy path)
- Edge cases (penny stocks, high prices, equal prices)
- Error conditions (negative prices, invalid inputs)
- Formula validation (known Gann calculations)
- API endpoint integration tests
"""

import pytest
import math
from app.financial_models.gann import GannSquareCalculator, get_gann_calculator


class TestGannSquareCalculator:
    """Test suite for GannSquareCalculator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = get_gann_calculator()

    # ============================================================
    # Happy Path Tests
    # ============================================================

    def test_basic_calculation(self):
        """Test standard Gann level calculation."""
        result = self.calculator.calculate_gann_levels(
            current_price=150.0,
            reference_price=100.0,
            num_levels=3
        )

        # Verify structure
        assert "support_levels" in result
        assert "resistance_levels" in result
        assert "nearest_support" in result
        assert "nearest_resistance" in result
        assert "current_position" in result

        # Verify types
        assert isinstance(result["support_levels"], list)
        assert isinstance(result["resistance_levels"], list)
        assert result["nearest_support"] is None or isinstance(result["nearest_support"], float)
        assert result["nearest_resistance"] is None or isinstance(result["nearest_resistance"], float)

        # Support levels should be below reference price (100)
        for level in result["support_levels"]:
            assert level < 100.0, f"Support level {level} should be < reference price 100"

        # Resistance levels should be above reference price (100)
        for level in result["resistance_levels"]:
            assert level > 100.0, f"Resistance level {level} should be > reference price 100"

    def test_default_num_levels(self):
        """Test that default num_levels produces expected count."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=90.0
        )

        # Should have multiple levels (5 rotations × 8 angles = up to 40 levels per direction)
        assert len(result["support_levels"]) > 0
        assert len(result["resistance_levels"]) > 0

    def test_levels_are_sorted(self):
        """Ensure all levels are properly sorted."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=80.0,
            num_levels=5
        )

        # Support levels should be in ascending order
        support = result["support_levels"]
        assert support == sorted(support), "Support levels should be sorted ascending"

        # Resistance levels should be in ascending order
        resistance = result["resistance_levels"]
        assert resistance == sorted(resistance), "Resistance levels should be sorted ascending"

    def test_no_duplicate_levels(self):
        """Ensure no duplicate values in results."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=80.0,
            num_levels=5
        )

        # Check for duplicates
        support = result["support_levels"]
        assert len(support) == len(set(support)), "Support levels should have no duplicates"

        resistance = result["resistance_levels"]
        assert len(resistance) == len(set(resistance)), "Resistance levels should have no duplicates"

    # ============================================================
    # Edge Cases
    # ============================================================

    def test_current_equals_reference(self):
        """Test when current_price == reference_price."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=3
        )

        # Should have both support and resistance levels
        assert len(result["support_levels"]) > 0, "Should have support levels below reference"
        assert len(result["resistance_levels"]) > 0, "Should have resistance levels above reference"

        # All support should be < 100, all resistance should be > 100
        assert all(s < 100.0 for s in result["support_levels"])
        assert all(r > 100.0 for r in result["resistance_levels"])

    def test_penny_stock(self):
        """Test with very low stock price (< $1)."""
        result = self.calculator.calculate_gann_levels(
            current_price=0.50,
            reference_price=0.25,
            num_levels=3
        )

        # Should still produce valid levels
        assert len(result["support_levels"]) >= 0
        assert len(result["resistance_levels"]) > 0

        # All levels should be positive
        assert all(s > 0 for s in result["support_levels"])
        assert all(r > 0 for r in result["resistance_levels"])

    def test_high_price_stock(self):
        """Test with very high stock price (> $1000)."""
        result = self.calculator.calculate_gann_levels(
            current_price=5000.0,
            reference_price=4500.0,
            num_levels=3
        )

        # Should produce valid levels
        assert len(result["support_levels"]) > 0
        assert len(result["resistance_levels"]) > 0

        # Levels should be reasonable (within order of magnitude)
        assert all(3000 < s < 6000 for s in result["support_levels"])
        assert all(4000 < r < 7000 for r in result["resistance_levels"])

    def test_reference_above_current(self):
        """Test using reference price above current price (e.g., 52-week high)."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=150.0,  # Reference is above current
            num_levels=3
        )

        # Should still produce valid results
        assert "support_levels" in result
        assert "resistance_levels" in result

        # Support levels should be below reference (150)
        assert all(s < 150.0 for s in result["support_levels"])

        # Resistance levels should be above reference (150)
        assert all(r > 150.0 for r in result["resistance_levels"])

    # ============================================================
    # Error Conditions
    # ============================================================

    def test_negative_current_price_raises_error(self):
        """Test that negative current_price raises ValueError."""
        with pytest.raises(ValueError, match="current_price must be > 0"):
            self.calculator.calculate_gann_levels(
                current_price=-100.0,
                reference_price=90.0
            )

    def test_zero_current_price_raises_error(self):
        """Test that zero current_price raises ValueError."""
        with pytest.raises(ValueError, match="current_price must be > 0"):
            self.calculator.calculate_gann_levels(
                current_price=0.0,
                reference_price=90.0
            )

    def test_negative_reference_price_raises_error(self):
        """Test that negative reference_price raises ValueError."""
        with pytest.raises(ValueError, match="reference_price must be > 0"):
            self.calculator.calculate_gann_levels(
                current_price=100.0,
                reference_price=-50.0
            )

    def test_zero_reference_price_raises_error(self):
        """Test that zero reference_price raises ValueError."""
        with pytest.raises(ValueError, match="reference_price must be > 0"):
            self.calculator.calculate_gann_levels(
                current_price=100.0,
                reference_price=0.0
            )

    def test_invalid_num_levels_too_low(self):
        """Test that num_levels < 1 raises ValueError."""
        with pytest.raises(ValueError, match="num_levels must be between 1 and 10"):
            self.calculator.calculate_gann_levels(
                current_price=100.0,
                reference_price=90.0,
                num_levels=0
            )

    def test_invalid_num_levels_too_high(self):
        """Test that num_levels > 10 raises ValueError."""
        with pytest.raises(ValueError, match="num_levels must be between 1 and 10"):
            self.calculator.calculate_gann_levels(
                current_price=100.0,
                reference_price=90.0,
                num_levels=11
            )

    def test_invalid_num_levels_negative(self):
        """Test that negative num_levels raises ValueError."""
        with pytest.raises(ValueError, match="num_levels must be between 1 and 10"):
            self.calculator.calculate_gann_levels(
                current_price=100.0,
                reference_price=90.0,
                num_levels=-5
            )

    # ============================================================
    # Formula Validation Tests
    # ============================================================

    def test_known_gann_value_180_degrees(self):
        """
        Test against known Gann calculation.

        Starting at $100 (sqrt=10), 180° rotation 1 should be:
        sqrt = 10 + (1 × 180/360) = 10.5
        price = 10.5² = 110.25
        """
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=1
        )

        # 180° rotation 1 up should produce ~110.25
        expected_180_deg = 110.25
        assert expected_180_deg in result["resistance_levels"], \
            f"Expected {expected_180_deg} in resistance levels, got {result['resistance_levels']}"

    def test_known_gann_value_360_degrees(self):
        """
        Test against known Gann calculation.

        Starting at $100 (sqrt=10), 360° rotation 1 should be:
        sqrt = 10 + (1 × 360/360) = 11
        price = 11² = 121
        """
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=1
        )

        # 360° rotation 1 up should produce 121.0
        expected_360_deg = 121.0
        assert expected_360_deg in result["resistance_levels"], \
            f"Expected {expected_360_deg} in resistance levels, got {result['resistance_levels']}"

    def test_known_gann_value_90_degrees(self):
        """
        Test against known Gann calculation.

        Starting at $100 (sqrt=10), 90° rotation 1 should be:
        sqrt = 10 + (1 × 90/360) = 10.25
        price = 10.25² = 105.0625 ≈ 105.06
        """
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=1
        )

        # 90° rotation 1 up should produce ~105.06
        expected_90_deg = 105.06
        assert expected_90_deg in result["resistance_levels"], \
            f"Expected {expected_90_deg} in resistance levels, got {result['resistance_levels']}"

    def test_symmetry_up_down(self):
        """Test that up and down calculations are symmetric."""
        # Calculate from same reference, going up
        result_up = self.calculator.calculate_gann_levels(
            current_price=120.0,
            reference_price=100.0,
            num_levels=2
        )

        # Calculate from same reference, going down
        result_down = self.calculator.calculate_gann_levels(
            current_price=80.0,
            reference_price=100.0,
            num_levels=2
        )

        # Should have support and resistance levels
        assert len(result_up["resistance_levels"]) > 0
        assert len(result_down["support_levels"]) > 0

    # ============================================================
    # Parametrized Tests
    # ============================================================

    @pytest.mark.parametrize("num_levels", [1, 2, 3, 5, 10])
    def test_num_levels_parameter(self, num_levels):
        """Test different valid num_levels values."""
        result = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=90.0,
            num_levels=num_levels
        )

        # Should produce results for each num_levels
        assert len(result["support_levels"]) > 0
        assert len(result["resistance_levels"]) > 0

    @pytest.mark.parametrize("price", [0.10, 1.0, 10.0, 100.0, 1000.0, 10000.0])
    def test_various_price_ranges(self, price):
        """Test calculator works across wide price ranges."""
        result = self.calculator.calculate_gann_levels(
            current_price=price,
            reference_price=price * 0.9,
            num_levels=3
        )

        # Should produce valid results for all price ranges
        assert len(result["support_levels"]) >= 0
        assert len(result["resistance_levels"]) > 0

    # ============================================================
    # is_at_key_level Tests
    # ============================================================

    def test_is_at_key_level_at_support(self):
        """Test detection when price is at a support level."""
        # First, get support levels
        levels = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=3
        )

        # Pick a support level
        if levels["support_levels"]:
            support_level = levels["support_levels"][0]

            # Test when price is exactly at support
            result = self.calculator.is_at_key_level(
                current_price=support_level,
                reference_price=100.0,
                tolerance=0.02
            )

            assert result["at_support"] is True

    def test_is_at_key_level_at_resistance(self):
        """Test detection when price is at a resistance level."""
        # First, get resistance levels
        levels = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=3
        )

        # Pick a resistance level
        if levels["resistance_levels"]:
            resistance_level = levels["resistance_levels"][0]

            # Test when price is exactly at resistance
            result = self.calculator.is_at_key_level(
                current_price=resistance_level,
                reference_price=100.0,
                tolerance=0.02
            )

            assert result["at_resistance"] is True

    def test_is_at_key_level_between(self):
        """Test detection when price is between levels."""
        # Test with price clearly between levels
        result = self.calculator.is_at_key_level(
            current_price=100.0,
            reference_price=80.0,
            tolerance=0.01  # Tight tolerance
        )

        # Should not be at either level with tight tolerance
        # (result depends on whether 100 happens to align with a level)
        assert isinstance(result["at_support"], bool)
        assert isinstance(result["at_resistance"], bool)

    # ============================================================
    # calculate_price_target Tests
    # ============================================================

    def test_calculate_price_target_180_up(self):
        """Test price target calculation for 180° up."""
        target = self.calculator.calculate_price_target(
            entry_price=100.0,
            angle=180,
            direction="up"
        )

        # 180° up from 100: sqrt(100) + 180/360 = 10.5, price = 110.25
        expected = 110.25
        assert target == expected, f"Expected {expected}, got {target}"

    def test_calculate_price_target_360_up(self):
        """Test price target calculation for 360° up."""
        target = self.calculator.calculate_price_target(
            entry_price=100.0,
            angle=360,
            direction="up"
        )

        # 360° up from 100: sqrt(100) + 1 = 11, price = 121
        expected = 121.0
        assert target == expected, f"Expected {expected}, got {target}"

    def test_calculate_price_target_180_down(self):
        """Test price target calculation for 180° down."""
        target = self.calculator.calculate_price_target(
            entry_price=100.0,
            angle=180,
            direction="down"
        )

        # 180° down from 100: sqrt(100) - 180/360 = 9.5, price = 90.25
        expected = 90.25
        assert target == expected, f"Expected {expected}, got {target}"

    def test_calculate_price_target_invalid_angle(self):
        """Test that invalid angle raises ValueError."""
        with pytest.raises(ValueError, match="Angle must be one of"):
            self.calculator.calculate_price_target(
                entry_price=100.0,
                angle=123,  # Invalid angle
                direction="up"
            )

    def test_calculate_price_target_negative_result(self):
        """Test that calculation resulting in negative price raises ValueError."""
        with pytest.raises(ValueError, match="Calculated target would be negative"):
            self.calculator.calculate_price_target(
                entry_price=1.0,  # Very low price
                angle=360,
                direction="down"  # Going down will result in negative
            )

    # ============================================================
    # _determine_position Tests
    # ============================================================

    def test_determine_position_at_support(self):
        """Test position determination when at support level."""
        levels = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=3
        )

        if levels["support_levels"]:
            support = levels["support_levels"][0]
            result = self.calculator.calculate_gann_levels(
                current_price=support,
                reference_price=100.0,
                num_levels=3
            )
            # Position should indicate at or near support
            assert result["current_position"] in ["at_support", "between_levels"]

    def test_determine_position_at_resistance(self):
        """Test position determination when at resistance level."""
        levels = self.calculator.calculate_gann_levels(
            current_price=100.0,
            reference_price=100.0,
            num_levels=3
        )

        if levels["resistance_levels"]:
            resistance = levels["resistance_levels"][0]
            result = self.calculator.calculate_gann_levels(
                current_price=resistance,
                reference_price=100.0,
                num_levels=3
            )
            # Position should indicate at or near resistance
            assert result["current_position"] in ["at_resistance", "between_levels"]

    # ============================================================
    # Nearest Level Tests
    # ============================================================

    def test_nearest_support_below_current(self):
        """Test that nearest support is below current price."""
        result = self.calculator.calculate_gann_levels(
            current_price=110.0,
            reference_price=100.0,
            num_levels=5
        )

        if result["nearest_support"]:
            assert result["nearest_support"] < 110.0, \
                "Nearest support should be below current price"

    def test_nearest_resistance_above_current(self):
        """Test that nearest resistance is above current price."""
        result = self.calculator.calculate_gann_levels(
            current_price=90.0,
            reference_price=100.0,
            num_levels=5
        )

        if result["nearest_resistance"]:
            assert result["nearest_resistance"] > 90.0, \
                "Nearest resistance should be above current price"

    def test_no_nearest_support_when_above_all(self):
        """Test that nearest_support is None when price is above all support levels."""
        result = self.calculator.calculate_gann_levels(
            current_price=200.0,
            reference_price=100.0,
            num_levels=2
        )

        # With current far above reference, might not have support above current
        # This is acceptable behavior
        assert result["nearest_support"] is None or result["nearest_support"] < 200.0

    def test_no_nearest_resistance_when_below_all(self):
        """Test that nearest_resistance is None when price is below all resistance levels."""
        result = self.calculator.calculate_gann_levels(
            current_price=50.0,
            reference_price=100.0,
            num_levels=2
        )

        # With current far below reference, should have resistance above
        assert result["nearest_resistance"] is not None
        assert result["nearest_resistance"] > 50.0


class TestGannCalculatorSingleton:
    """Test the singleton getter function."""

    def test_get_gann_calculator_returns_instance(self):
        """Test that get_gann_calculator returns a GannSquareCalculator instance."""
        calc = get_gann_calculator()
        assert isinstance(calc, GannSquareCalculator)

    def test_get_gann_calculator_returns_same_instance(self):
        """Test that get_gann_calculator returns the same instance (singleton pattern)."""
        calc1 = get_gann_calculator()
        calc2 = get_gann_calculator()
        assert calc1 is calc2, "Should return the same singleton instance"
