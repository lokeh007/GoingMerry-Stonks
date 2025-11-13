"""
Gann Square of 9 Calculator Module.

This module implements W.D. Gann's Square of 9 mathematical technique
for identifying key support and resistance levels in stock prices.

## Overview

The Square of 9 is a spiral-based price calculator where numbers increase
outward from a center point. The spiral progresses through "rings," with
each complete rotation (360°) representing a full cycle. Key angles within
each rotation mark important price levels.

## Mathematical Foundation

The core formula is based on square roots and angular relationships:

    sqrt(price) = sqrt(reference_price) ± (rotation × angle / 360)
    price = sqrt(price)²

Where:
- reference_price: Starting point (typically 52-week low or significant price level)
- rotation: Distance from center (1, 2, 3, ...)
- angle: Position on the spiral (0° to 360°)

### Example Calculation

Starting at $100 (sqrt = 10):
- 90° rotation 1:  sqrt = 10 + (1 × 90/360)  = 10.25  → $105.06
- 180° rotation 1: sqrt = 10 + (1 × 180/360) = 10.5   → $110.25
- 270° rotation 1: sqrt = 10 + (1 × 270/360) = 10.75  → $115.56
- 360° rotation 1: sqrt = 10 + (1 × 360/360) = 11     → $121.00

## Key Angles and Their Significance

### Cardinal Angles (Primary Levels)
- **0°/360°**: Full rotation, strongest resistance/support
- **90°**: Quarter cycle, significant level
- **180°**: Half cycle, most important level in Gann theory
- **270°**: Three-quarter cycle, significant level

### Diagonal Angles (Secondary Levels)
- **45°**: Northeast diagonal, minor resistance/support
- **135°**: Northwest diagonal, minor resistance/support
- **225°**: Southwest diagonal, minor resistance/support
- **315°**: Southeast diagonal, minor resistance/support

In traditional Gann analysis, cardinal angles are considered stronger
than diagonal angles.

## Usage Example

```python
from app.financial_models.gann import get_gann_calculator

calculator = get_gann_calculator()

# Calculate levels for a stock at $150 with 52-week low at $100
levels = calculator.calculate_gann_levels(
    current_price=150.0,
    reference_price=100.0,
    num_levels=5
)

print(f"Support levels: {levels['support_levels']}")
print(f"Resistance levels: {levels['resistance_levels']}")
print(f"Nearest support: ${levels['nearest_support']:.2f}")
print(f"Nearest resistance: ${levels['nearest_resistance']:.2f}")
print(f"Position: {levels['current_position']}")
```

## Limitations

This implementation focuses on **price levels only**. Traditional Gann
analysis also includes:
- Time cycles (days/weeks from significant dates)
- Speed angles (1×1, 2×1, etc.)
- Natural squares of time (30, 90, 120, 144 days)

Future enhancements may add time-based calculations for complete
Gann Square of 9 functionality.

## References

- Gann, W.D. "The Basis of My Forecasting Method" (1935)
- Trading literature on Gann Square of 9 methodology
- Various technical analysis references on Gann theory
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Gann Square of 9 Constants
# ============================================================

# Cardinal angles (strongest levels) - 90°, 180°, 270°, 360°
CARDINAL_ANGLES = [90, 180, 270, 360]

# Diagonal angles (secondary levels) - 45°, 135°, 225°, 315°
DIAGONAL_ANGLES = [45, 135, 225, 315]

# All key angles combined
KEY_ANGLES = CARDINAL_ANGLES + DIAGONAL_ANGLES


# ============================================================
# Helper Functions
# ============================================================

def _calculate_price_at_angle(
    center_price: float, angle: int, rotation: int, direction: str
) -> float:
    """
    Calculate price at specific angle and rotation on Gann Square of 9 spiral.

    This is a shared helper function used by both the cached calculation
    and the class methods to ensure consistency.

    Args:
        center_price: Reference/center price for the calculation
        angle: Angle in degrees (45, 90, 135, 180, 225, 270, 315, 360)
        rotation: Rotation number (1, 2, 3, ...) representing distance from center
        direction: 'up' for resistance, 'down' for support

    Returns:
        Calculated price at the specified angle and rotation

    Example:
        >>> _calculate_price_at_angle(100.0, 180, 1, "up")
        110.25  # sqrt(100) + (1 * 180/360) = 10.5, then 10.5^2 = 110.25
    """
    sqrt_center = math.sqrt(center_price)
    angular_increment = (angle / 360.0) * rotation

    if direction == "up":
        price_sqrt = sqrt_center + angular_increment
    else:
        price_sqrt = sqrt_center - angular_increment

    if price_sqrt <= 0:
        return 0

    return price_sqrt ** 2


@dataclass
class GannLevel:
    """
    Represents a single Gann Square of 9 support or resistance level.

    Attributes:
        price: The calculated price level
        angle: The angle in degrees (45, 90, 135, 180, 225, 270, 315, 360)
        rotation: The rotation number (1, 2, 3, ...)
        strength: Level strength ('major' for cardinal angles, 'minor' for diagonal angles)
        distance_pct: Distance from current price as percentage (positive = above, negative = below)
        level_type: 'support' or 'resistance'
    """
    price: float
    angle: int
    rotation: int
    strength: str
    distance_pct: float
    level_type: str


@lru_cache(maxsize=1000)
def _calculate_gann_levels_cached(
    current_price: float,
    reference_price: float,
    num_levels: int,
) -> Tuple[List[float], List[float]]:
    """
    Cached calculation of Gann support and resistance levels.

    This function is cached to avoid redundant calculations when the same
    parameters are used repeatedly. The cache can store up to 1000 different
    parameter combinations.

    Args:
        current_price: Current stock price
        reference_price: Reference price (52-week low or high)
        num_levels: Number of levels to calculate in each direction

    Returns:
        Tuple of (support_levels, resistance_levels)

    Note:
        This is a module-level function (not a method) to enable LRU caching.
        Instance methods cannot be effectively cached with lru_cache.

        The tolerance parameter is intentionally NOT part of the cache key because
        it only affects position classification (via _determine_position()), not the
        actual price level calculations. This allows the same calculated levels to be
        reused with different tolerance thresholds for ~100x performance improvement.
    """
    # Calculate support levels (below reference price)
    support_levels = []
    for rotation in range(1, num_levels + 1):
        for angle in KEY_ANGLES:
            price = _calculate_price_at_angle(reference_price, angle, rotation, "down")
            if price > 0 and price < reference_price:
                support_levels.append(round(price, 2))

    # Calculate resistance levels (above reference price)
    resistance_levels = []
    for rotation in range(1, num_levels + 1):
        for angle in KEY_ANGLES:
            price = _calculate_price_at_angle(reference_price, angle, rotation, "up")
            if price > reference_price:
                resistance_levels.append(round(price, 2))

    # Remove duplicates and sort
    support_levels = sorted(list(set(support_levels)))
    resistance_levels = sorted(list(set(resistance_levels)))

    logger.debug(
        f"Calculated {len(support_levels)} support and "
        f"{len(resistance_levels)} resistance levels for "
        f"current={current_price:.2f}, ref={reference_price:.2f}, num_levels={num_levels}"
    )

    return (support_levels, resistance_levels)


class GannSquareCalculator:
    """
    Calculator for Gann Square of 9 support and resistance levels.

    The Square of 9 uses a mathematical spiral to calculate price targets
    based on angular relationships.

    Cardinal Angles (Primary levels):
    - 90° (0.25 rotation): Quarter-cycle support/resistance
    - 180° (0.5 rotation): Half-cycle, strongest support/resistance
    - 270° (0.75 rotation): Three-quarter cycle support/resistance
    - 360° (1.0 rotation): Complete cycle, major support/resistance

    Diagonal Angles (Secondary levels):
    - 45° (0.125 rotation): Minor support/resistance
    - 135° (0.375 rotation): Minor support/resistance
    - 225° (0.625 rotation): Minor support/resistance
    - 315° (0.875 rotation): Minor support/resistance

    In Gann theory, cardinal angles (0°, 90°, 180°, 270°) are considered
    stronger than diagonal angles (45°, 135°, 225°, 315°).

    Note: This class uses the module-level constants CARDINAL_ANGLES,
    DIAGONAL_ANGLES, and KEY_ANGLES defined at the top of this file.
    """

    # Number of levels to calculate up and down
    DEFAULT_LEVELS = 5

    def calculate_gann_levels_with_metadata(
        self,
        current_price: float,
        reference_price: Optional[float] = None,
        num_levels: int = DEFAULT_LEVELS,
        tolerance: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Calculate Gann levels with detailed metadata for each level.

        This method returns structured GannLevel objects with angle, rotation,
        strength, and distance information for each calculated level.

        Args:
            current_price: Current stock price
            reference_price: Reference price (52-week low or high). If None, uses current_price
            num_levels: Number of levels to calculate in each direction
            tolerance: Price tolerance as percentage for determining position

        Returns:
            Dict containing structured level data with metadata
        """
        # Validate inputs
        if current_price <= 0:
            raise ValueError(f"current_price must be > 0, got {current_price}")

        if reference_price is not None and reference_price <= 0:
            raise ValueError(f"reference_price must be > 0, got {reference_price}")

        if not 1 <= num_levels <= 10:
            raise ValueError(f"num_levels must be between 1 and 10, got {num_levels}")

        if not 0.001 <= tolerance <= 0.10:
            raise ValueError(f"tolerance must be between 0.001 and 0.10, got {tolerance}")

        if reference_price is None:
            reference_price = current_price

        # Calculate levels with detailed metadata
        support_levels_detailed: List[GannLevel] = []
        resistance_levels_detailed: List[GannLevel] = []

        for rotation in range(1, num_levels + 1):
            for angle in KEY_ANGLES:
                # Calculate price for this angle and rotation
                price_down = self._calculate_gann_price_at_angle(
                    reference_price, angle, rotation, "down"
                )
                price_up = self._calculate_gann_price_at_angle(
                    reference_price, angle, rotation, "up"
                )

                # Determine strength based on angle type
                # Cardinal angles (90, 180, 270, 360) are major
                # Diagonal angles (45, 135, 225, 315) are minor
                strength = "major" if angle in CARDINAL_ANGLES else "minor"

                # Add support level if valid
                if price_down > 0 and price_down < reference_price:
                    distance_pct = ((price_down - current_price) / current_price) * 100
                    support_levels_detailed.append(GannLevel(
                        price=round(price_down, 2),
                        angle=angle,
                        rotation=rotation,
                        strength=strength,
                        distance_pct=round(distance_pct, 2),
                        level_type="support"
                    ))

                # Add resistance level if valid
                if price_up > reference_price:
                    distance_pct = ((price_up - current_price) / current_price) * 100
                    resistance_levels_detailed.append(GannLevel(
                        price=round(price_up, 2),
                        angle=angle,
                        rotation=rotation,
                        strength=strength,
                        distance_pct=round(distance_pct, 2),
                        level_type="resistance"
                    ))

        # Remove duplicates based on price, prioritizing 'major' strength and lowest rotation
        def _prioritize_levels(levels: List[GannLevel]) -> List[GannLevel]:
            """
            Remove duplicate prices, keeping the most significant level.

            When multiple angle/rotation combinations produce the same price,
            prioritize by:
            1. Strength: 'major' (cardinal angles) over 'minor' (diagonal angles)
            2. Rotation: Lower rotation numbers over higher (closer to reference)

            This ensures we keep the most meaningful level when duplicates exist.
            """
            price_to_levels: Dict[float, List[GannLevel]] = defaultdict(list)
            for level in levels:
                price_to_levels[level.price].append(level)

            prioritized = []
            for price, group in price_to_levels.items():
                # Sort by: 1) strength ('major' first), 2) rotation (lower first)
                best_level = sorted(
                    group,
                    key=lambda x: (0 if x.strength == "major" else 1, x.rotation)
                )[0]
                prioritized.append(best_level)

            return prioritized

        # Apply prioritization to both support and resistance levels
        support_levels_detailed = _prioritize_levels(support_levels_detailed)
        resistance_levels_detailed = _prioritize_levels(resistance_levels_detailed)

        # Sort by price
        support_levels_detailed = sorted(support_levels_detailed, key=lambda x: x.price)
        resistance_levels_detailed = sorted(resistance_levels_detailed, key=lambda x: x.price)

        # Find nearest levels
        support_below = [s for s in support_levels_detailed if s.price < current_price]
        nearest_support = max(support_below, key=lambda x: x.price) if support_below else None

        resistance_above = [r for r in resistance_levels_detailed if r.price > current_price]
        nearest_resistance = min(resistance_above, key=lambda x: x.price) if resistance_above else None

        # Determine position
        position = self._determine_position(
            current_price,
            nearest_support.price if nearest_support else None,
            nearest_resistance.price if nearest_resistance else None,
            tolerance=tolerance
        )

        return {
            "current_price": current_price,
            "reference_price": reference_price,
            "support_levels": [level.__dict__ for level in support_levels_detailed],
            "resistance_levels": [level.__dict__ for level in resistance_levels_detailed],
            "nearest_support": nearest_support.__dict__ if nearest_support else None,
            "nearest_resistance": nearest_resistance.__dict__ if nearest_resistance else None,
            "current_position": position,
        }

    def calculate_gann_levels(
        self,
        current_price: float,
        reference_price: Optional[float] = None,
        num_levels: int = DEFAULT_LEVELS,
        tolerance: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Calculate Gann Square of 9 support and resistance levels.

        Args:
            current_price: Current stock price
            reference_price: Reference price (52-week low or high). If None, uses current_price
            num_levels: Number of levels to calculate in each direction
            tolerance: Price tolerance as percentage for determining position (default: 0.02 = 2%)

        Returns:
            Dict containing:
            - support_levels: List of support prices
            - resistance_levels: List of resistance prices
            - current_position: Position relative to nearest key level
            - nearest_support: Closest support level below current price
            - nearest_resistance: Closest resistance level above current price
        """
        try:
            # Validate inputs
            if current_price <= 0:
                raise ValueError(f"current_price must be > 0, got {current_price}")

            if reference_price is not None and reference_price <= 0:
                raise ValueError(f"reference_price must be > 0, got {reference_price}")

            if not 1 <= num_levels <= 10:
                raise ValueError(f"num_levels must be between 1 and 10, got {num_levels}")

            if not 0.001 <= tolerance <= 0.10:
                raise ValueError(f"tolerance must be between 0.001 and 0.10, got {tolerance}")

            if reference_price is None:
                reference_price = current_price

            # Warn if prices are very different
            if abs(current_price - reference_price) / current_price > 0.5:
                logger.warning(
                    f"Large price gap: current=${current_price:.2f}, "
                    f"reference=${reference_price:.2f} "
                    f"({abs(1 - reference_price/current_price)*100:.0f}% difference)"
                )

            logger.info(
                f"Calculating Gann levels: current={current_price:.2f}, "
                f"reference={reference_price:.2f}"
            )

            # Use cached calculation for performance
            # Round current_price to nearest $0.10 to improve cache hit rate
            current_price_rounded = round(current_price * 10) / 10
            support_levels, resistance_levels = _calculate_gann_levels_cached(
                current_price=current_price_rounded,
                reference_price=reference_price,
                num_levels=num_levels,
            )

            # Find nearest levels to current price
            nearest_support = self._find_nearest_support(current_price, support_levels)
            nearest_resistance = self._find_nearest_resistance(
                current_price, resistance_levels
            )

            # Determine current position
            position = self._determine_position(
                current_price, nearest_support, nearest_resistance, tolerance=tolerance
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
                f"Gann levels calculated: support={nearest_support if nearest_support is None else f'{nearest_support:.2f}'}, "
                f"resistance={nearest_resistance if nearest_resistance is None else f'{nearest_resistance:.2f}'}, position={position}"
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

    def _calculate_gann_price_at_angle(
        self, center_price: float, angle: int, rotation: int, direction: str = "up"
    ) -> float:
        """
        Calculate price at specific angle and rotation on Gann Square of 9 spiral.

        The Gann Square of 9 is a price spiral where each full rotation (360°)
        adds approximately 2 to the square root of the price. Key angles
        represent important support/resistance levels.

        Formula:
            sqrt(price) = sqrt(center_price) ± (rotation × angle / 360)
            price = sqrt(price)²

        Args:
            center_price: Reference/center price for the calculation
            angle: Angle in degrees (90, 180, 270, 360)
            rotation: Rotation number (1, 2, 3, ...) representing distance from center
            direction: 'up' for resistance, 'down' for support

        Returns:
            Calculated price at the specified angle and rotation

        Example:
            Starting at $100 (sqrt=10):
            - 180° rotation 1 up: sqrt=10+(1×180/360)=10.5, price=110.25
            - 360° rotation 1 up: sqrt=10+(1×360/360)=11, price=121
            - Full rotation (360°) always adds 1 to sqrt, or ~21% to price
        """
        # Delegate to the module-level helper function to avoid code duplication
        return _calculate_price_at_angle(center_price, angle, rotation, direction)

    def _calculate_levels(
        self, reference_price: float, direction: str, num_levels: int
    ) -> List[float]:
        """
        Calculate support or resistance levels using Gann Square of 9 spiral formula.

        The Square of 9 uses a mathematical spiral where numbers increase outward
        from the center. Key angles (90°, 180°, 270°, 360°) represent important
        price levels based on Gann's geometric relationships.

        Args:
            reference_price: Starting price (typically 52-week low/high)
            direction: 'up' for resistance, 'down' for support
            num_levels: Number of rotation levels to calculate

        Returns:
            List of calculated price levels, filtered by direction
        """
        levels = []
        sqrt_ref = math.sqrt(reference_price)

        logger.debug(
            f"Calculating {num_levels} levels in '{direction}' direction from ${reference_price:.2f}"
        )

        for rotation in range(1, num_levels + 1):
            for angle in KEY_ANGLES:
                # Calculate price at this angle and rotation
                price = self._calculate_gann_price_at_angle(
                    center_price=reference_price,
                    angle=angle,
                    rotation=rotation,
                    direction=direction
                )

                if price > 0:
                    levels.append(round(price, 2))
                    logger.debug(
                        f"  Rotation {rotation}, Angle {angle:3d}°: ${price:8.2f} "
                        f"(sqrt={math.sqrt(price):.4f})"
                    )

        # Remove duplicates and sort
        raw_count = len(levels)
        levels = sorted(list(set(levels)))
        logger.debug(f"Generated {raw_count} levels, {len(levels)} unique after deduplication")

        # Filter levels based on direction
        if direction == "up":
            # For resistance, keep only levels above reference
            levels = [l for l in levels if l > reference_price]
        else:
            # For support, keep only levels below reference
            levels = [l for l in levels if l < reference_price]

        logger.debug(f"Filtered to {len(levels)} levels {direction} from reference price")
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
        tolerance: float = 0.02,
    ) -> str:
        """
        Determine current position relative to key levels.

        Args:
            current_price: Current stock price
            nearest_support: Nearest support level
            nearest_resistance: Nearest resistance level
            tolerance: Price tolerance as percentage (default: 0.02 = 2%)

        Returns:
            Position description: 'at_support', 'at_resistance', 'between_levels', 'unknown'
        """

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
        if angle not in KEY_ANGLES:
            raise ValueError(f"Angle must be one of {KEY_ANGLES}")

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

    # ============================================================
    # Time Dimension Methods (Gann Price-Time Calculator)
    # ============================================================

    def calculate_time_cycles(
        self, entry_date: str, cycle_type: str = "natural"
    ) -> Dict[str, Any]:
        """
        Calculate Gann time cycles from a significant date.

        Gann's time cycles are based on natural squares and astronomical cycles.
        Key time periods: 30, 60, 90, 120, 144, 180, 360 days.

        Args:
            entry_date: Starting date in YYYY-MM-DD format
            cycle_type: Type of cycle ('natural', 'cardinal', 'all')

        Returns:
            Dict containing cycle dates and their significance

        Example:
            >>> calc.calculate_time_cycles("2024-01-01", "natural")
            {
                "entry_date": "2024-01-01",
                "cycles": [
                    {"days": 30, "date": "2024-01-31", "significance": "minor"},
                    {"days": 90, "date": "2024-04-01", "significance": "major"},
                    ...
                ]
            }
        """
        from datetime import datetime, timedelta

        try:
            start_date = datetime.strptime(entry_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {entry_date}. Use YYYY-MM-DD")

        # Gann's natural time cycles
        natural_cycles = [30, 60, 90, 120, 144, 180, 240, 270, 360]

        # Cardinal cycles (quarters)
        cardinal_cycles = [90, 180, 270, 360]

        # Diagonal cycles (45° increments)
        diagonal_cycles = [45, 135, 225, 315]

        if cycle_type == "natural":
            cycles_to_use = natural_cycles
        elif cycle_type == "cardinal":
            cycles_to_use = cardinal_cycles
        elif cycle_type == "diagonal":
            cycles_to_use = diagonal_cycles
        else:  # "all"
            cycles_to_use = sorted(set(natural_cycles + diagonal_cycles))

        cycle_dates = []
        for days in cycles_to_use:
            target_date = start_date + timedelta(days=days)

            # Determine significance based on cycle length
            if days in [90, 180, 360]:
                significance = "major"
            elif days in [30, 60, 120, 270]:
                significance = "moderate"
            else:
                significance = "minor"

            cycle_dates.append({
                "days": days,
                "date": target_date.strftime("%Y-%m-%d"),
                "significance": significance,
                "description": self._get_cycle_description(days)
            })

        logger.info(
            f"Calculated {len(cycle_dates)} time cycles from {entry_date}"
        )

        return {
            "entry_date": entry_date,
            "cycle_type": cycle_type,
            "cycles": cycle_dates
        }

    def calculate_time_to_price_target(
        self,
        entry_price: float,
        target_price: float,
        entry_date: str,
        speed_angle: str = "1x1"
    ) -> Dict[str, Any]:
        """
        Calculate estimated time to reach a price target using Gann angles.

        Gann speed angles represent the relationship between price and time:
        - 1x1: 1 point of price per 1 unit of time (45° angle, balanced)
        - 2x1: 2 points of price per 1 unit of time (steeper, faster move)
        - 1x2: 1 point of price per 2 units of time (gentler, slower move)

        Args:
            entry_price: Starting price
            target_price: Target price to reach
            entry_date: Entry date in YYYY-MM-DD format
            speed_angle: Gann speed angle ('1x1', '2x1', '1x2')

        Returns:
            Dict containing estimated target date and time period

        Note:
            This is a simplified implementation. True Gann analysis requires
            detailed price-time square charting and manual analysis.
        """
        from datetime import datetime, timedelta

        if entry_price <= 0 or target_price <= 0:
            raise ValueError("Prices must be positive")

        try:
            start_date = datetime.strptime(entry_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {entry_date}. Use YYYY-MM-DD")

        # Calculate price distance in square root space
        sqrt_entry = math.sqrt(entry_price)
        sqrt_target = math.sqrt(target_price)
        sqrt_distance = abs(sqrt_target - sqrt_entry)

        # Speed angle determines time per unit of sqrt distance
        # 1x1 = balanced (1 day per 0.01 sqrt unit as baseline)
        # 2x1 = faster (0.5 days per 0.01 sqrt unit)
        # 1x2 = slower (2 days per 0.01 sqrt unit)
        speed_multipliers = {
            "1x1": 1.0,
            "2x1": 0.5,
            "1x2": 2.0,
            "1x3": 3.0,
            "3x1": 0.33
        }

        if speed_angle not in speed_multipliers:
            raise ValueError(f"Invalid speed angle. Use one of {list(speed_multipliers.keys())}")

        # Baseline: 100 days per full unit of sqrt distance (approximation)
        baseline_days_per_unit = 100
        speed_factor = speed_multipliers[speed_angle]

        estimated_days = int(sqrt_distance * baseline_days_per_unit * speed_factor)
        target_date = start_date + timedelta(days=estimated_days)

        direction = "up" if target_price > entry_price else "down"
        price_change_pct = ((target_price / entry_price) - 1) * 100

        logger.info(
            f"Time to target: {entry_price:.2f} → {target_price:.2f} "
            f"at {speed_angle} angle: {estimated_days} days"
        )

        return {
            "entry_price": entry_price,
            "target_price": target_price,
            "entry_date": entry_date,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "estimated_days": estimated_days,
            "speed_angle": speed_angle,
            "direction": direction,
            "price_change_pct": round(price_change_pct, 2),
            "sqrt_distance": round(sqrt_distance, 4),
            "note": "This is an approximation. Actual market movements vary significantly."
        }

    def calculate_price_at_time(
        self,
        entry_price: float,
        entry_date: str,
        target_date: str,
        speed_angle: str = "1x1",
        direction: str = "up"
    ) -> Dict[str, Any]:
        """
        Calculate expected price at a future date using Gann speed angles.

        Args:
            entry_price: Starting price
            entry_date: Entry date in YYYY-MM-DD format
            target_date: Target date in YYYY-MM-DD format
            speed_angle: Gann speed angle ('1x1', '2x1', '1x2', etc.)
            direction: 'up' for bullish, 'down' for bearish

        Returns:
            Dict containing estimated price at target date

        Note:
            This is a theoretical calculation based on Gann principles.
            Real market prices depend on many factors beyond time-price geometry.
        """
        from datetime import datetime

        if entry_price <= 0:
            raise ValueError("entry_price must be positive")

        try:
            start_date = datetime.strptime(entry_date, "%Y-%m-%d")
            end_date = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

        # Calculate time difference
        days_diff = (end_date - start_date).days

        if days_diff < 0:
            raise ValueError("target_date must be after entry_date")

        # Speed angle determines price movement rate
        speed_multipliers = {
            "1x1": 1.0,
            "2x1": 2.0,
            "1x2": 0.5,
            "1x3": 0.33,
            "3x1": 3.0
        }

        if speed_angle not in speed_multipliers:
            raise ValueError(f"Invalid speed angle. Use one of {list(speed_multipliers.keys())}")

        # Baseline: 0.01 sqrt unit per 100 days (approximation)
        baseline_sqrt_change_per_100_days = 0.01
        speed_factor = speed_multipliers[speed_angle]

        sqrt_entry = math.sqrt(entry_price)
        sqrt_change = (days_diff / 100) * baseline_sqrt_change_per_100_days * speed_factor

        if direction == "up":
            sqrt_target = sqrt_entry + sqrt_change
        else:
            sqrt_target = sqrt_entry - sqrt_change

        if sqrt_target <= 0:
            raise ValueError("Calculated price would be negative or zero")

        target_price = sqrt_target ** 2
        price_change_pct = ((target_price / entry_price) - 1) * 100

        logger.info(
            f"Price at time: {entry_price:.2f} on {entry_date} → "
            f"{target_price:.2f} on {target_date} at {speed_angle} {direction}"
        )

        return {
            "entry_price": entry_price,
            "entry_date": entry_date,
            "target_date": target_date,
            "target_price": round(target_price, 2),
            "days_elapsed": days_diff,
            "speed_angle": speed_angle,
            "direction": direction,
            "price_change_pct": round(price_change_pct, 2),
            "sqrt_change": round(sqrt_change, 4),
            "note": "This is a theoretical calculation for educational purposes."
        }

    def _get_cycle_description(self, days: int) -> str:
        """
        Get description of a Gann time cycle.

        Args:
            days: Number of days in the cycle

        Returns:
            Description of the cycle's significance
        """
        descriptions = {
            30: "1-month cycle (minor turning point)",
            45: "45-day diagonal cycle",
            60: "2-month cycle",
            90: "Quarter cycle (major turning point)",
            120: "4-month cycle",
            135: "135-day diagonal cycle",
            144: "144-day natural square cycle (12²)",
            180: "Half-year cycle (major turning point)",
            225: "225-day diagonal cycle",
            240: "8-month cycle",
            270: "Three-quarter year cycle",
            315: "315-day diagonal cycle",
            360: "Annual cycle (major turning point)"
        }

        return descriptions.get(days, f"{days}-day cycle")


# Singleton instance
_gann_calculator = GannSquareCalculator()


def get_gann_calculator() -> GannSquareCalculator:
    """
    Get the singleton Gann calculator instance.

    Returns:
        GannSquareCalculator instance
    """
    return _gann_calculator
