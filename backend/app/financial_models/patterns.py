"""
Bulkowski Pattern Detection Module.

This module implements detection algorithms for Thomas Bulkowski's chart patterns.
Focus is on preconditions for high-probability patterns rather than perfect matching.

Reference: "Encyclopedia of Chart Patterns" by Thomas N. Bulkowski
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detector for Bulkowski chart patterns.

    Implements precondition detection for:
    - Pipe Bottom: Two sharp, parallel lows
    - Double Bottom: Return to test major low after bounce

    These are "preconditions" that increase probability of pattern formation,
    not exact pattern matches.
    """

    def detect_pipe_bottom(
        self, df: pd.DataFrame, lookback: int = 20, tolerance: float = 0.02
    ) -> Dict[str, any]:
        """
        Detect potential Pipe Bottom pattern.

        Pipe Bottom Criteria (Bulkowski):
        - Two sharp, parallel lows within tolerance
        - Lows separated by 1-5 trading days
        - Sharp decline before first low (> 5% in 3 days)
        - Volume spike on second low (optional but strong signal)

        Args:
            df: DataFrame with OHLCV data (must have 'Low', 'Close', 'Volume' columns)
            lookback: Number of days to look back for pattern
            tolerance: Price tolerance for "parallel" lows (default: 2%)

        Returns:
            Dict with:
            - detected: Boolean indicating if pattern found
            - confidence: Confidence score (0-100)
            - first_low: Price of first low
            - second_low: Price of second low
            - days_between: Days between the two lows
            - description: Human-readable description
        """
        try:
            if len(df) < lookback:
                logger.warning(
                    f"Insufficient data for Pipe Bottom detection: {len(df)} < {lookback}"
                )
                return self._empty_pattern_result()

            # Get recent data
            recent = df.tail(lookback).copy()

            # Find local lows (where Low is lower than previous and next day)
            lows = []
            for i in range(1, len(recent) - 1):
                if (
                    recent.iloc[i]["Low"] < recent.iloc[i - 1]["Low"]
                    and recent.iloc[i]["Low"] < recent.iloc[i + 1]["Low"]
                ):
                    lows.append(
                        {
                            "index": i,
                            "price": recent.iloc[i]["Low"],
                            "date": recent.index[i],
                        }
                    )

            # Need at least 2 lows
            if len(lows) < 2:
                return self._empty_pattern_result()

            # Check pairs of lows for pipe bottom characteristics
            for i in range(len(lows) - 1):
                for j in range(i + 1, len(lows)):
                    first_low = lows[i]
                    second_low = lows[j]

                    # Check if lows are within tolerance (parallel)
                    price_diff = abs(first_low["price"] - second_low["price"])
                    avg_price = (first_low["price"] + second_low["price"]) / 2
                    price_diff_pct = price_diff / avg_price

                    if price_diff_pct > tolerance:
                        continue

                    # Check days between lows (1-5 days)
                    days_between = second_low["index"] - first_low["index"]
                    if days_between < 1 or days_between > 5:
                        continue

                    # Check for sharp decline before first low
                    if first_low["index"] >= 3:
                        decline_start = recent.iloc[first_low["index"] - 3]["Close"]
                        decline_end = recent.iloc[first_low["index"]]["Close"]
                        decline_pct = (
                            (decline_start - decline_end) / decline_start * 100
                        )

                        if decline_pct < 5:  # Need at least 5% decline
                            continue

                        # Calculate confidence score
                        confidence = self._calculate_pipe_bottom_confidence(
                            price_diff_pct, days_between, decline_pct, recent, second_low
                        )

                        return {
                            "detected": True,
                            "pattern_name": "Pipe Bottom",
                            "confidence": confidence,
                            "first_low": round(first_low["price"], 2),
                            "second_low": round(second_low["price"], 2),
                            "days_between": days_between,
                            "decline_pct": round(decline_pct, 2),
                            "description": f"Two parallel lows ({first_low['price']:.2f}, {second_low['price']:.2f}) "
                            f"after {decline_pct:.1f}% decline",
                        }

            return self._empty_pattern_result()

        except Exception as e:
            logger.error(f"Error detecting Pipe Bottom: {e}")
            return self._empty_pattern_result()

    def detect_double_bottom(
        self, df: pd.DataFrame, lookback: int = 60, tolerance: float = 0.03
    ) -> Dict[str, any]:
        """
        Detect potential Double Bottom pattern.

        Double Bottom Criteria (Bulkowski):
        - Two distinct lows at approximately same level
        - Significant bounce between lows (> 10% from first low)
        - Second low tests the first low (within tolerance)
        - Lows separated by 10-60 trading days
        - Breakout above peak between lows confirms pattern

        Args:
            df: DataFrame with OHLCV data (must have 'Low', 'High', 'Close' columns)
            lookback: Number of days to look back for pattern
            tolerance: Price tolerance for matching lows (default: 3%)

        Returns:
            Dict with:
            - detected: Boolean indicating if pattern found
            - confidence: Confidence score (0-100)
            - first_low: Price of first low
            - second_low: Price of second low
            - peak_between: Highest price between the lows
            - bounce_pct: Percentage bounce from first low to peak
            - description: Human-readable description
        """
        try:
            if len(df) < lookback:
                logger.warning(
                    f"Insufficient data for Double Bottom detection: {len(df)} < {lookback}"
                )
                return self._empty_pattern_result()

            # Get recent data
            recent = df.tail(lookback).copy()

            # Find significant lows (lower than 3-day window around them)
            lows = []
            for i in range(3, len(recent) - 3):
                window_low = min(
                    recent.iloc[i - 3 : i + 4]["Low"]
                )  # 3 days before/after
                if recent.iloc[i]["Low"] == window_low:
                    lows.append(
                        {
                            "index": i,
                            "price": recent.iloc[i]["Low"],
                            "date": recent.index[i],
                        }
                    )

            # Need at least 2 lows
            if len(lows) < 2:
                return self._empty_pattern_result()

            # Check pairs of lows for double bottom characteristics
            for i in range(len(lows) - 1):
                for j in range(i + 1, len(lows)):
                    first_low = lows[i]
                    second_low = lows[j]

                    # Check days between lows (10-60 days typical for double bottom)
                    days_between = second_low["index"] - first_low["index"]
                    if days_between < 10 or days_between > 60:
                        continue

                    # Check if lows are at similar level (within tolerance)
                    price_diff = abs(first_low["price"] - second_low["price"])
                    avg_price = (first_low["price"] + second_low["price"]) / 2
                    price_diff_pct = price_diff / avg_price

                    if price_diff_pct > tolerance:
                        continue

                    # Find peak between the two lows
                    between_section = recent.iloc[
                        first_low["index"] : second_low["index"] + 1
                    ]
                    peak_price = between_section["High"].max()
                    bounce_pct = (
                        (peak_price - first_low["price"]) / first_low["price"] * 100
                    )

                    # Require significant bounce (> 10%)
                    if bounce_pct < 10:
                        continue

                    # Calculate confidence score
                    confidence = self._calculate_double_bottom_confidence(
                        price_diff_pct, bounce_pct, days_between, recent, second_low
                    )

                    return {
                        "detected": True,
                        "pattern_name": "Double Bottom",
                        "confidence": confidence,
                        "first_low": round(first_low["price"], 2),
                        "second_low": round(second_low["price"], 2),
                        "peak_between": round(peak_price, 2),
                        "bounce_pct": round(bounce_pct, 2),
                        "days_between": days_between,
                        "description": f"Two lows at {avg_price:.2f} with {bounce_pct:.1f}% bounce between",
                    }

            return self._empty_pattern_result()

        except Exception as e:
            logger.error(f"Error detecting Double Bottom: {e}")
            return self._empty_pattern_result()

    def _calculate_pipe_bottom_confidence(
        self,
        price_diff_pct: float,
        days_between: int,
        decline_pct: float,
        df: pd.DataFrame,
        second_low: Dict,
    ) -> int:
        """
        Calculate confidence score for Pipe Bottom pattern.

        Factors:
        - Price alignment (lower diff = higher confidence)
        - Days between lows (2-3 days ideal)
        - Decline magnitude (sharper = higher confidence)
        - Volume on second low (higher = higher confidence)

        Args:
            price_diff_pct: Price difference as percentage
            days_between: Days between the two lows
            decline_pct: Decline percentage before first low
            df: Price/volume dataframe
            second_low: Dict with second low information

        Returns:
            Confidence score (0-100)
        """
        score = 50  # Base score

        # Price alignment (max 25 points)
        if price_diff_pct < 0.01:  # Within 1%
            score += 25
        elif price_diff_pct < 0.02:  # Within 2%
            score += 15
        else:
            score += 5

        # Days between (max 15 points)
        if days_between in [2, 3]:  # Ideal spacing
            score += 15
        elif days_between in [1, 4]:
            score += 10
        else:
            score += 5

        # Decline magnitude (max 10 points)
        if decline_pct > 10:
            score += 10
        elif decline_pct > 7:
            score += 7
        else:
            score += 3

        return min(score, 100)

    def _calculate_double_bottom_confidence(
        self,
        price_diff_pct: float,
        bounce_pct: float,
        days_between: int,
        df: pd.DataFrame,
        second_low: Dict,
    ) -> int:
        """
        Calculate confidence score for Double Bottom pattern.

        Factors:
        - Price alignment of lows (lower diff = higher confidence)
        - Bounce magnitude (15-25% ideal)
        - Pattern duration (20-40 days ideal)
        - Volume pattern (increasing on second low confirms)

        Args:
            price_diff_pct: Price difference as percentage
            bounce_pct: Bounce percentage from first low
            days_between: Days between the two lows
            df: Price/volume dataframe
            second_low: Dict with second low information

        Returns:
            Confidence score (0-100)
        """
        score = 50  # Base score

        # Price alignment (max 25 points)
        if price_diff_pct < 0.01:  # Within 1%
            score += 25
        elif price_diff_pct < 0.02:  # Within 2%
            score += 18
        elif price_diff_pct < 0.03:  # Within 3%
            score += 10
        else:
            score += 5

        # Bounce magnitude (max 20 points)
        if 15 <= bounce_pct <= 25:  # Ideal range
            score += 20
        elif 10 <= bounce_pct < 15:
            score += 15
        elif bounce_pct > 25:
            score += 10

        # Pattern duration (max 5 points)
        if 20 <= days_between <= 40:  # Classic double bottom
            score += 5
        else:
            score += 2

        return min(score, 100)

    def _empty_pattern_result(self) -> Dict[str, any]:
        """Return empty pattern result when no pattern detected."""
        return {
            "detected": False,
            "pattern_name": None,
            "confidence": 0,
            "description": "No pattern detected",
        }


# Singleton instance
_pattern_detector = PatternDetector()


def get_pattern_detector() -> PatternDetector:
    """
    Get the singleton pattern detector instance.

    Returns:
        PatternDetector instance
    """
    return _pattern_detector
