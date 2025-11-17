"""
Firestore data serialization utilities.

This module provides functions to convert numpy/pandas types to native Python types
for Firestore compatibility. Firestore cannot serialize numpy types directly, so
all data must be converted before saving.

See: https://cloud.google.com/firestore/docs/manage-data/add-data#data_types
"""

from datetime import datetime, date
from typing import Any
import numpy as np
import pandas as pd


def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy/pandas types to native Python types for Firestore compatibility.

    Firestore cannot serialize numpy types (numpy.bool_, numpy.int64, numpy.float64, etc.)
    or pandas types (pd.Timestamp, pd.NA, NaT, etc.). This function ensures all values
    are native Python types before saving to Firestore.

    Handles:
    - Dictionaries (recursively converts all values)
    - Lists (recursively converts all items)
    - NumPy boolean types (np.bool_)
    - NumPy signed integers (np.int8, np.int16, np.int32, np.int64)
    - NumPy unsigned integers (np.uint8, np.uint16, np.uint32, np.uint64)
    - NumPy floats (np.float16, np.float32, np.float64)
    - NumPy arrays (converts to Python list)
    - NaN/None/pd.NA/pd.NaT (converts to None)
    - Pandas Timestamps (converts to Python datetime)
    - Python datetime/date objects (already compatible)

    Args:
        obj: Object to convert (dict, list, scalar, or any nested structure)

    Returns:
        Object with all numpy/pandas types converted to Python native types

    Examples:
        >>> convert_numpy_types(np.int64(42))
        42
        >>> convert_numpy_types({"value": np.float64(3.14)})
        {'value': 3.14}
        >>> convert_numpy_types([np.nan, None, pd.NA])
        [None, None, None]
        >>> convert_numpy_types(pd.Timestamp("2023-01-01"))
        datetime.datetime(2023, 1, 1, 0, 0)
    """
    # Handle None and NaN-like values FIRST (before type checking)
    # pd.isna() handles: None, np.nan, pd.NA, pd.NaT, float('nan')
    if pd.isna(obj):
        return None

    # Handle dictionaries (recursively convert all values)
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}

    # Handle lists (recursively convert all items)
    if isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]

    # Handle NumPy boolean types
    if isinstance(obj, np.bool_):
        return bool(obj)

    # Handle NumPy signed integer types
    if isinstance(obj, (np.int8, np.int16, np.int32, np.int64)):
        return int(obj)

    # Handle NumPy unsigned integer types (new!)
    if isinstance(obj, (np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)

    # Handle NumPy float types
    if isinstance(obj, (np.float16, np.float32, np.float64)):
        # Check for NaN in float type (defensive - pd.isna should catch this)
        if np.isnan(obj):
            return None
        return float(obj)

    # Handle NumPy arrays (convert to Python list)
    if isinstance(obj, np.ndarray):
        return obj.tolist()

    # Handle Pandas Timestamps (convert to Python datetime)
    if isinstance(obj, pd.Timestamp):
        return obj.to_pydatetime()

    # Handle Python datetime/date objects (already Firestore-compatible, but be explicit)
    if isinstance(obj, (datetime, date)):
        return obj

    # All other types (str, int, float, bool, etc.) are already Firestore-compatible
    return obj
