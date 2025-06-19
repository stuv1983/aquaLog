# utils/validation.py

"""
validation.py – Data Validation and Sanitization

Provides data validation functions for the application. Includes helpers for
sanity-checking user-entered parameter readings and identifying out-of-range
values against safe limits, both global hard limits and user-defined custom ranges.
"""

import pandas as pd  
from typing import Any, Optional
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS
from .chemistry import nh3_fraction
# FIXED: Import the repository instead of the legacy function
from aqualog_db.repositories import CustomRangeRepository 

# Hard physical limits for parameter sanity checks.
# These limits represent the absolute plausible range for each parameter,
# beyond which a reading is considered physically impossible or erroneous.
# Format: "parameter_name": (minimum_plausible_value, maximum_plausible_value)
HARD_LIMITS: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 40.0),  # Temperature in Celsius
    "ph":          (0.0, 14.0),  # pH scale
    "ammonia":     (0.0, 10.0),  # Ammonia in ppm
    "nitrite":     (0.0, 10.0),  # Nitrite in ppm
    "nitrate":     (0.0, 500.0), # Nitrate in ppm
    "kh":          (0.0, 20.0),  # Carbonate Hardness in dKH
    "gh":          (0.0, 30.0),  # General Hardness in dGH
}



def arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures that the 'date' column in a Pandas DataFrame is of `datetime64[ns]` dtype.
    This is necessary for compatibility with Streamlit's Arrow serialization,
    which can otherwise cause issues when displaying DataFrames with date columns.

    Args:
        df: The input Pandas DataFrame.

    Returns:
        pd.DataFrame: A copy of the DataFrame with the 'date' column coerced to
                      `datetime64[ns]`. Non-coercible values become NaT (Not a Time).
    """
    if "date" in df.columns and df["date"].dtype != "datetime64[ns]":
        df = df.copy() # Create a copy to avoid modifying the original DataFrame
        df["date"] = pd.to_datetime(df["date"], errors="coerce") # Coerce to datetime, invalid parsing results in NaT
    return df


def validate_reading(param: str, value: float) -> None:
    """
    Validates a single parameter reading against globally plausible hard limits.
    If the `value` falls outside these predefined `HARD_LIMITS` for the given
    `param`, a `ValueError` is raised.

    Args:
        param: The name of the parameter (e.g., "temperature", "ph").
        value: The numeric reading of the parameter.

    Raises:
        ValueError: If `value` is outside the plausible range for `param`.
    """
    limits = HARD_LIMITS.get(param)
    if not limits:
        # If no hard limits are defined for the parameter, no validation is performed.
        return
    lo, hi = limits
    if value < lo or value > hi:
        raise ValueError(f"{param.upper()} reading {value} is outside plausible range ({lo}–{hi}).")

def is_too_low(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is below its configured `TOO_LOW_THRESHOLDS`.

    Args:
        param: The name of the parameter.
        value: The numeric reading of the parameter.

    Returns:
        bool: True if `value` is less than the threshold (and a threshold is defined),
              False otherwise.
    """
    thresh = TOO_LOW_THRESHOLDS.get(param)
    # Returns True if a threshold exists and the value is below it.
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is above its configured `TOO_HIGH_THRESHOLDS`.

    Args:
        param: The name of the parameter.
        value: The numeric reading of the parameter.

    Returns:
        bool: True if `value` is greater than the threshold (and a threshold is defined),
              False otherwise.
    """
    thresh = TOO_HIGH_THRESHOLDS.get(param)
    # Returns True if a threshold exists and the value is above it.
    return thresh is not None and value > thresh

def is_out_of_range(
    param: str,
    value: Any, # Can be float, pd.Series, or string (for co2_indicator)
    *, # Enforce keyword-only arguments from here
    tank_id: int,
    ph: Optional[float] = None, # Required for ammonia calculation
    temp_c: Optional[float] = None, # Required for ammonia calculation
) -> bool:
    """
    Determines if a parameter's value is outside the safe range configured for a specific tank.
    This function considers custom ranges defined for the tank, falling back to global
    `SAFE_RANGES` if no custom range is set.
    Special handling is included for unionized ammonia and categorical CO₂ indicator.

    Args:
        param: The name of the parameter (e.g., "ammonia", "ph", "co2_indicator").
        value: The measured value of the parameter. Can be a float, pandas Series,
               or string (for "co2_indicator").
        tank_id: The ID of the tank, used to retrieve any custom safe ranges.
        ph: Optional. The pH value, required if `param` is "ammonia" for unionized
            ammonia calculation.
        temp_c: Optional. The temperature in Celsius, required if `param` is "ammonia".

    Returns:
        bool: True if the value is outside the safe range, False otherwise.
    """

    # Special-case handling for unionized ammonia, which depends on pH and temperature.
    if param == "ammonia" and ph is not None and temp_c is not None:
        try:
            # Calculate the toxic unionized ammonia fraction.
            nh3 = nh3_fraction(value, ph, temp_c)
            # If the input value was a Series, nh3 will also be a Series.
            if isinstance(nh3, pd.Series):
                # Check if ANY value in the series is above the ammonia high threshold.
                return nh3.gt(TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)).any()
            # For single float value, directly compare.
            return nh3 > TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)
        except Exception:
            # If calculation fails (e.g., invalid input types), assume not out of range to be safe.
            return False

    # Special-case handling for CO₂ indicator, which is categorical (color-based).
    if param == "co2_indicator":
        if isinstance(value, pd.Series):
            # For Series, check if any value is not "Green" (the ideal state).
            return (~value.eq("Green")).any()
        # For single value, check if it's a string and not "Green".
        return isinstance(value, str) and value != "Green"

    # FIXED: Use the repository to get custom ranges dynamically for the tank.
    custom_range_repo = CustomRangeRepository() 
    custom = custom_range_repo.get(tank_id, param) # Get custom range (low, high) or None
    
    # Determine the safe range: custom if available, otherwise global SAFE_RANGES.
    lo, hi = custom if custom else SAFE_RANGES.get(param, (None, None))
    if lo is None or hi is None:
        # If no safe range (custom or global) is defined, the parameter cannot be out of range.
        return False

    # Numeric checks for all other parameters.
    if isinstance(value, pd.Series):
        # For Pandas Series, check if any value is less than low OR greater than high.
        return (value.lt(lo) | value.gt(hi)).any()

    try:
        val = float(value) # Attempt to convert value to float for comparison.
        return val < lo or val > hi
    except (TypeError, ValueError):
        # If value cannot be converted to float (e.g., non-numeric string), it's not considered
        # out of range for numeric checks (might be handled by specific checks above, e.g., co2_indicator).
        return False