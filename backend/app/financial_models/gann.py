"""
Gann Square of 9 Calculator Module.

This module implements W.D. Gann's Square of 9 mathematical technique
for identifying key support and resistance levels in stock prices.

The Square of 9 is a spiral starting at 1 in the center, with numbers
increasing outward. Key angles (90°, 180°, 270°, 360°) represent
important price levels.
"""

import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GannSquareCalculator:
    """
    Calculator for Gann Square of 9 support and resistance levels.

    The Square of 9 uses a mathematical spiral to calculate price targets
    based on angular relationships. Key angles:
    - 90° (0.25 rotation): Minor support/resistance
    - 180° (0.5 rotation): Major support/resistance
    - 270° (0.75 rotation): Minor support/resistance
    - 360° (1.0 rotation): Complete cycle, strongest levels
    """

    # Key angles in degrees
    KEY_ANGLES = [90, 180, 270, 360]

    # Number of levels to calculate up and down
    DEFAULT_LEVELS = 5

    def calculate_gann_levels(
        self,
        current_price: float,
        reference_price: Optional[float] = None,
        num_levels: int = DEFAULT_LEVELS,
    ) -> Dict[str, any]:
        """
        Calculate Gann Square of 9 support and resistance levels.

        Args:
            current_price: Current stock price
            reference_price: Reference price (52-week low or high). If None, uses current_price
            num_levels: Number of levels to calculate in each direction

        Returns:
            Dict containing:
            - support_levels: List of support prices
            - resistance_levels: List of resistance prices
            - current_position: Position relative to nearest key level
            - nearest_support: Closest support level below current price
            - nearest_resistance: Closest resistance level above current price
        """
        try:
            if reference_price is None:
                reference_price = current_price

            logger.info(
                f"Calculating Gann levels: current={current_price:.2f}, "
                f"reference={reference_price:.2f}"
            )

            # Calculate support levels (below current price)
            support_levels = self._calculate_levels(
                reference_price, direction="down", num_levels=num_levels
            )

            # Calculate resistance levels (above current price)
            resistance_levels = self._calculate_levels(
                reference_price, direction="up", num_levels=num_levels
            )

            # Find nearest levels to current price
            nearest_support = self._find_nearest_support(current_price, support_levels)
            nearest_resistance = self._find_nearest_resistance(
                current_price, resistance_levels
            )

            # Determine current position
            position = self._determine_position(
                current_price, nearest_support, nearest_resistance
            )

            result = {
                "current_price": current_price,
                "reference_price": reference_price,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "nearest_support": nearest_support,
                "nearest_resistance": nearest_resistance,
                "current_position": position,
            }

            logger.info(
                f"Gann levels calculated: support={nearest_support:.2f}, "
                f"resistance={nearest_resistance:.2f}, position={position}"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating Gann levels: {e}")
            raise ValueError(f"Failed to calculate Gann levels: {str(e)}")

    def is_at_key_level(
        self, current_price: float, reference_price: float, tolerance: float = 0.02
    ) -> Dict[str, bool]:
        """
        Check if current price is at a key Gann level.

        Args:
            current_price: Current stock price
            reference_price: Reference price (52-week low or high)
            tolerance: Price tolerance as percentage (default: 2%)

        Returns:
            Dict with 'at_support' and 'at_resistance' boolean flags
        """
        try:
            levels = self.calculate_gann_levels(current_price, reference_price)

            # Check if within tolerance of support
            at_support = False
            if levels["nearest_support"]:
                support_diff = abs(current_price - levels["nearest_support"])
                at_support = support_diff / current_price <= tolerance

            # Check if within tolerance of resistance
            at_resistance = False
            if levels["nearest_resistance"]:
                resistance_diff = abs(current_price - levels["nearest_resistance"])
                at_resistance = resistance_diff / current_price <= tolerance

            return {"at_support": at_support, "at_resistance": at_resistance}

        except Exception as e:
            logger.error(f"Error checking key levels: {e}")
            return {"at_support": False, "at_resistance": False}

    def _calculate_levels(
        self, reference_price: float, direction: str, num_levels: int
    ) -> List[float]:
        """
        Calculate support or resistance levels using Square of 9 formula.

        Formula: value = (sqrt(reference) + angle/360) ^ 2

        Args:
            reference_price: Starting price
            direction: 'up' for resistance, 'down' for support
            num_levels: Number of levels to calculate

        Returns:
            List of price levels
        """
        levels = []
        sqrt_ref = math.sqrt(reference_price)

        for i in range(1, num_levels + 1):
            for angle in self.KEY_ANGLES:
                # Calculate angular distance
                rotations = angle / 360.0

                if direction == "up":
                    # Add rotations for resistance
                    sqrt_value = sqrt_ref + (rotations * i)
                else:
                    # Subtract rotations for support
                    sqrt_value = sqrt_ref - (rotations * i)

                # Ensure we don't get negative sqrt values
                if sqrt_value > 0:
                    level = sqrt_value**2
                    levels.append(round(level, 2))

        # Remove duplicates and sort
        levels = sorted(list(set(levels)))

        if direction == "up":
            # For resistance, filter levels above reference
            levels = [l for l in levels if l > reference_price]
        else:
            # For support, filter levels below reference
            levels = [l for l in levels if l < reference_price]

        return levels

    def _find_nearest_support(
        self, current_price: float, support_levels: List[float]
    ) -> Optional[float]:
        """
        Find the nearest support level below current price.

        Args:
            current_price: Current stock price
            support_levels: List of support price levels

        Returns:
            Nearest support level or None
        """
        below_price = [s for s in support_levels if s < current_price]
        return max(below_price) if below_price else None

    def _find_nearest_resistance(
        self, current_price: float, resistance_levels: List[float]
    ) -> Optional[float]:
        """
        Find the nearest resistance level above current price.

        Args:
            current_price: Current stock price
            resistance_levels: List of resistance price levels

        Returns:
            Nearest resistance level or None
        """
        above_price = [r for r in resistance_levels if r > current_price]
        return min(above_price) if above_price else None

    def _determine_position(
        self,
        current_price: float,
        nearest_support: Optional[float],
        nearest_resistance: Optional[float],
    ) -> str:
        """
        Determine current position relative to key levels.

        Args:
            current_price: Current stock price
            nearest_support: Nearest support level
            nearest_resistance: Nearest resistance level

        Returns:
            Position description: 'at_support', 'at_resistance', 'between', 'unknown'
        """
        tolerance = 0.02  # 2% tolerance

        if nearest_support:
            support_diff = abs(current_price - nearest_support) / current_price
            if support_diff <= tolerance:
                return "at_support"

        if nearest_resistance:
            resistance_diff = abs(current_price - nearest_resistance) / current_price
            if resistance_diff <= tolerance:
                return "at_resistance"

        if nearest_support and nearest_resistance:
            return "between_levels"

        return "unknown"

    def calculate_price_target(
        self, entry_price: float, angle: int = 180, direction: str = "up"
    ) -> float:
        """
        Calculate price target based on Gann angle from entry price.

        Args:
            entry_price: Entry/current price
            angle: Gann angle (90, 180, 270, 360)
            direction: 'up' for bullish target, 'down' for bearish target

        Returns:
            Target price

        Raises:
            ValueError: If angle is not a key angle
        """
        if angle not in self.KEY_ANGLES:
            raise ValueError(f"Angle must be one of {self.KEY_ANGLES}")

        sqrt_price = math.sqrt(entry_price)
        rotation = angle / 360.0

        if direction == "up":
            target_sqrt = sqrt_price + rotation
        else:
            target_sqrt = sqrt_price - rotation

        if target_sqrt <= 0:
            raise ValueError("Calculated target would be negative or zero")

        target = target_sqrt**2

        logger.info(
            f"Price target: entry={entry_price:.2f}, angle={angle}°, "
            f"direction={direction}, target={target:.2f}"
        )

        return round(target, 2)


# Singleton instance
_gann_calculator = GannSquareCalculator()


def get_gann_calculator() -> GannSquareCalculator:
    """
    Get the singleton Gann calculator instance.

    Returns:
        GannSquareCalculator instance
    """
    return _gann_calculator
