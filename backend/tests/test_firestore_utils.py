"""
Unit tests for Firestore utility functions.

Tests comprehensive type conversion for numpy/pandas types to ensure
Firestore compatibility.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date, timezone

from app.utils.firestore import convert_numpy_types


class TestConvertNumpyTypes:
    """Test suite for convert_numpy_types function."""

    # ========================
    # Test Basic Types
    # ========================

    def test_native_python_types_unchanged(self):
        """Native Python types should pass through unchanged."""
        assert convert_numpy_types(42) == 42
        assert convert_numpy_types(3.14) == 3.14
        assert convert_numpy_types("hello") == "hello"
        assert convert_numpy_types(True) is True
        assert convert_numpy_types(False) is False

    def test_none_unchanged(self):
        """None should remain None."""
        assert convert_numpy_types(None) is None

    # ========================
    # Test NumPy Boolean Types
    # ========================

    def test_numpy_bool(self):
        """NumPy bool_ types should convert to Python bool."""
        assert convert_numpy_types(np.bool_(True)) is True
        assert convert_numpy_types(np.bool_(False)) is False
        assert isinstance(convert_numpy_types(np.bool_(True)), bool)

    # ========================
    # Test NumPy Signed Integer Types
    # ========================

    def test_numpy_signed_integers(self):
        """NumPy signed integer types should convert to Python int."""
        assert convert_numpy_types(np.int8(42)) == 42
        assert convert_numpy_types(np.int16(1000)) == 1000
        assert convert_numpy_types(np.int32(100000)) == 100000
        assert convert_numpy_types(np.int64(1000000)) == 1000000

        # Verify return type is Python int
        assert isinstance(convert_numpy_types(np.int64(42)), int)

    def test_numpy_signed_integers_negative(self):
        """NumPy signed integers should handle negative values."""
        assert convert_numpy_types(np.int8(-42)) == -42
        assert convert_numpy_types(np.int16(-1000)) == -1000
        assert convert_numpy_types(np.int32(-100000)) == -100000
        assert convert_numpy_types(np.int64(-1000000)) == -1000000

    # ========================
    # Test NumPy Unsigned Integer Types (NEW!)
    # ========================

    def test_numpy_unsigned_integers(self):
        """NumPy unsigned integer types should convert to Python int."""
        assert convert_numpy_types(np.uint8(255)) == 255
        assert convert_numpy_types(np.uint16(65535)) == 65535
        assert convert_numpy_types(np.uint32(4294967295)) == 4294967295
        assert convert_numpy_types(np.uint64(18446744073709551615)) == 18446744073709551615

        # Verify return type is Python int
        assert isinstance(convert_numpy_types(np.uint32(42)), int)

    def test_numpy_unsigned_integers_zero(self):
        """NumPy unsigned integers should handle zero."""
        assert convert_numpy_types(np.uint8(0)) == 0
        assert convert_numpy_types(np.uint16(0)) == 0
        assert convert_numpy_types(np.uint32(0)) == 0
        assert convert_numpy_types(np.uint64(0)) == 0

    # ========================
    # Test NumPy Float Types
    # ========================

    def test_numpy_floats(self):
        """NumPy float types should convert to Python float."""
        assert convert_numpy_types(np.float16(3.14)) == pytest.approx(3.14, rel=1e-2)
        assert convert_numpy_types(np.float32(3.14159)) == pytest.approx(3.14159, rel=1e-6)
        assert convert_numpy_types(np.float64(3.141592653589793)) == pytest.approx(3.141592653589793)

        # Verify return type is Python float
        assert isinstance(convert_numpy_types(np.float64(3.14)), float)

    def test_numpy_floats_special_values(self):
        """NumPy floats should handle inf and -inf."""
        assert convert_numpy_types(np.float32(float('inf'))) == float('inf')
        assert convert_numpy_types(np.float64(float('-inf'))) == float('-inf')

    # ========================
    # Test NaN Handling (CRITICAL!)
    # ========================

    def test_numpy_nan(self):
        """NumPy NaN should convert to None."""
        assert convert_numpy_types(np.nan) is None
        assert convert_numpy_types(float('nan')) is None

    def test_numpy_float_nan(self):
        """NumPy float types containing NaN should convert to None."""
        assert convert_numpy_types(np.float32(np.nan)) is None
        assert convert_numpy_types(np.float64(np.nan)) is None

    def test_pandas_na(self):
        """Pandas NA should convert to None."""
        assert convert_numpy_types(pd.NA) is None

    def test_pandas_nat(self):
        """Pandas NaT (Not-a-Time) should convert to None."""
        assert convert_numpy_types(pd.NaT) is None

    # ========================
    # Test NumPy Arrays
    # ========================

    def test_numpy_array_1d(self):
        """1D NumPy arrays should convert to Python list."""
        arr = np.array([1, 2, 3, 4, 5])
        result = convert_numpy_types(arr)
        assert result == [1, 2, 3, 4, 5]
        assert isinstance(result, list)

    def test_numpy_array_2d(self):
        """2D NumPy arrays should convert to nested Python lists."""
        arr = np.array([[1, 2], [3, 4]])
        result = convert_numpy_types(arr)
        assert result == [[1, 2], [3, 4]]
        assert isinstance(result, list)
        assert isinstance(result[0], list)

    def test_numpy_array_with_nan(self):
        """NumPy arrays containing NaN should have NaN converted to None."""
        arr = np.array([1.0, 2.0, np.nan, 4.0])
        result = convert_numpy_types(arr)
        assert result[0] == 1.0
        assert result[1] == 2.0
        assert result[2] is None  # NaN -> None
        assert result[3] == 4.0

    # ========================
    # Test Pandas Timestamp
    # ========================

    def test_pandas_timestamp(self):
        """Pandas Timestamp should convert to Python datetime."""
        ts = pd.Timestamp("2023-01-01 12:00:00")
        result = convert_numpy_types(ts)
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_pandas_timestamp_with_timezone(self):
        """Pandas Timestamp with timezone should preserve timezone info."""
        ts = pd.Timestamp("2023-01-01 12:00:00", tz="UTC")
        result = convert_numpy_types(ts)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    # ========================
    # Test Python datetime/date (Already Compatible)
    # ========================

    def test_python_datetime(self):
        """Python datetime should remain unchanged."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = convert_numpy_types(dt)
        assert result == dt
        assert isinstance(result, datetime)

    def test_python_date(self):
        """Python date should remain unchanged."""
        d = date(2023, 1, 1)
        result = convert_numpy_types(d)
        assert result == d
        assert isinstance(result, date)

    # ========================
    # Test Recursive Conversion (Dicts)
    # ========================

    def test_dict_simple(self):
        """Simple dict with numpy types should convert recursively."""
        data = {
            "int": np.int64(42),
            "float": np.float64(3.14),
            "bool": np.bool_(True),
        }
        result = convert_numpy_types(data)
        assert result == {"int": 42, "float": 3.14, "bool": True}
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["bool"], bool)

    def test_dict_nested(self):
        """Nested dicts should convert recursively."""
        data = {
            "level1": {
                "level2": {
                    "value": np.int64(42)
                }
            }
        }
        result = convert_numpy_types(data)
        assert result == {"level1": {"level2": {"value": 42}}}
        assert isinstance(result["level1"]["level2"]["value"], int)

    def test_dict_with_nan(self):
        """Dict containing NaN should convert NaN to None."""
        data = {
            "valid": np.float64(3.14),
            "invalid": np.nan,
            "none": None,
        }
        result = convert_numpy_types(data)
        assert result == {"valid": 3.14, "invalid": None, "none": None}

    # ========================
    # Test Recursive Conversion (Lists)
    # ========================

    def test_list_simple(self):
        """Simple list with numpy types should convert recursively."""
        data = [np.int64(1), np.float64(2.0), np.bool_(True)]
        result = convert_numpy_types(data)
        assert result == [1, 2.0, True]
        assert isinstance(result[0], int)
        assert isinstance(result[1], float)
        assert isinstance(result[2], bool)

    def test_list_nested(self):
        """Nested lists should convert recursively."""
        data = [[np.int64(1), np.int64(2)], [np.int64(3), np.int64(4)]]
        result = convert_numpy_types(data)
        assert result == [[1, 2], [3, 4]]
        assert isinstance(result[0][0], int)

    def test_list_with_nan(self):
        """List containing NaN should convert NaN to None."""
        data = [np.float64(1.0), np.nan, None, pd.NA]
        result = convert_numpy_types(data)
        assert result == [1.0, None, None, None]

    # ========================
    # Test Complex Nested Structures
    # ========================

    def test_complex_nested_structure(self):
        """Complex nested structure should convert recursively."""
        data = {
            "results": [
                {
                    "ticker": "AAPL",
                    "price": np.float64(150.25),
                    "volume": np.int64(1000000),
                    "has_options": np.bool_(True),
                    "metrics": {
                        "pe_ratio": np.float32(25.5),
                        "market_cap": np.uint64(2500000000000),
                    },
                },
                {
                    "ticker": "GOOGL",
                    "price": np.float64(2800.50),
                    "volume": np.int64(500000),
                    "has_options": np.bool_(False),
                    "metrics": {
                        "pe_ratio": np.nan,  # Missing data
                        "market_cap": np.uint64(1800000000000),
                    },
                },
            ],
            "timestamp": pd.Timestamp("2023-01-01 12:00:00"),
        }

        result = convert_numpy_types(data)

        # Verify structure
        assert len(result["results"]) == 2
        assert result["results"][0]["ticker"] == "AAPL"
        assert result["results"][0]["price"] == 150.25
        assert result["results"][0]["volume"] == 1000000
        assert result["results"][0]["has_options"] is True
        assert result["results"][0]["metrics"]["pe_ratio"] == pytest.approx(25.5, rel=1e-6)
        assert result["results"][0]["metrics"]["market_cap"] == 2500000000000

        # Verify NaN handling
        assert result["results"][1]["metrics"]["pe_ratio"] is None

        # Verify timestamp conversion
        assert isinstance(result["timestamp"], datetime)

        # Verify all types are Python native
        assert isinstance(result["results"][0]["price"], float)
        assert isinstance(result["results"][0]["volume"], int)
        assert isinstance(result["results"][0]["has_options"], bool)
        assert isinstance(result["results"][0]["metrics"]["market_cap"], int)

    # ========================
    # Test Real-World Screener Data
    # ========================

    def test_screener_result_structure(self):
        """Test with realistic screener result structure."""
        screener_result = {
            "ticker": "TSLA",
            "company_name": "Tesla Inc",
            "current_price": np.float64(250.75),
            "market_cap": np.int64(800000000000),
            "score": np.float32(87.5),
            "institutional_ownership": np.float64(45.2),
            "analyst_count": np.int32(25),
            "has_insider_buying": np.bool_(True),
            "peg_ratio": np.float64(1.25),
            "eps_growth": np.float32(35.5),
            "last_updated": pd.Timestamp("2023-11-15 16:00:00"),
            "metadata": {
                "source": "yfinance",
                "api_calls": np.uint16(3),
            },
        }

        result = convert_numpy_types(screener_result)

        # Verify all conversions
        assert isinstance(result["current_price"], float)
        assert isinstance(result["market_cap"], int)
        assert isinstance(result["score"], float)
        assert isinstance(result["institutional_ownership"], float)
        assert isinstance(result["analyst_count"], int)
        assert isinstance(result["has_insider_buying"], bool)
        assert isinstance(result["peg_ratio"], float)
        assert isinstance(result["eps_growth"], float)
        assert isinstance(result["last_updated"], datetime)
        assert isinstance(result["metadata"]["api_calls"], int)

        # Verify values
        assert result["current_price"] == 250.75
        assert result["market_cap"] == 800000000000
        assert result["has_insider_buying"] is True

    def test_screener_result_with_missing_data(self):
        """Test screener result with missing/NaN values."""
        screener_result = {
            "ticker": "UNKNOWN",
            "current_price": np.float64(10.5),
            "peg_ratio": np.nan,  # Missing fundamental data
            "eps_growth": None,  # No data available
            "institutional_ownership": pd.NA,  # Pandas missing value
        }

        result = convert_numpy_types(screener_result)

        # All missing values should be None
        assert result["peg_ratio"] is None
        assert result["eps_growth"] is None
        assert result["institutional_ownership"] is None
        assert result["current_price"] == 10.5

    # ========================
    # Test Edge Cases
    # ========================

    def test_empty_dict(self):
        """Empty dict should remain empty."""
        assert convert_numpy_types({}) == {}

    def test_empty_list(self):
        """Empty list should remain empty."""
        assert convert_numpy_types([]) == []

    def test_empty_numpy_array(self):
        """Empty NumPy array should convert to empty list."""
        arr = np.array([])
        result = convert_numpy_types(arr)
        assert result == []
        assert isinstance(result, list)

    def test_mixed_types_list(self):
        """List with mixed Python and NumPy types should convert correctly."""
        data = [
            42,  # Python int
            np.int64(100),  # NumPy int
            3.14,  # Python float
            np.float64(2.71),  # NumPy float
            "hello",  # String
            True,  # Python bool
            np.bool_(False),  # NumPy bool
            None,  # None
            np.nan,  # NaN
        ]
        result = convert_numpy_types(data)
        assert result == [42, 100, 3.14, 2.71, "hello", True, False, None, None]
