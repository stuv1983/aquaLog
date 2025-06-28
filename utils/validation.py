# utils/validation.py

"""
validation.py – Data Validation and Sanitization

Provides data validation functions for the application. Includes helpers for
sanity-checking user-entered parameter readings and identifying out-of-range
values against safe limits, both global hard limits and user-defined custom ranges.
"""

from __future__ import annotations

import pandas as pd
from typing import Any, Optional, Tuple
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS, CO2_ON_SCHEDULE # Corrected import here
from datetime import time # Import time for comparison

from .chemistry import nh3_fraction
from aqualog_db.repositories import CustomRangeRepository, TankRepository

# Hard physical limits for parameter sanity checks.
# These limits represent the absolute plausible range for each parameter,
# beyond which a reading is considered physically impossible or erroneous,
# regardless of user-defined safe ranges. They are used to catch data entry errors.
# Format: "parameter_name": (minimum_plausible_value, maximum_plausible_value)
HARD_LIMITS: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 40.0),  # Temperature in Celsius
    "ph":          (0.0, 14.0),  # pH scale (0 to 14)
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
        df (pd.DataFrame): The input Pandas DataFrame.

    Returns:
        pd.DataFrame: A copy of the DataFrame with the 'date' column coerced to
                      `datetime64[ns]`. Non-coercible values in the 'date' column
                      will become `NaT` (Not a Time).
    """
    if "date" in df.columns and df["date"].dtype != "datetime64[ns]":
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def validate_reading(param: str, value: float) -> None:
    """
    Validates a single parameter reading against globally defined `HARD_LIMITS`.
    If the `value` falls outside these predefined absolute plausible limits for the given
    `param`, a `ValueError` is raised, indicating a likely data entry error.

    Args:
        param (str): The name of the parameter (e.g., "temperature", "ph").
        value (float): The numeric reading of the parameter.

    Raises:
        ValueError: If `value` is outside the plausible `HARD_LIMITS` range for `param`.
    """
    limits = HARD_LIMITS.get(param)
    if not limits:
        return
    lo, hi = limits
    if value < lo or value > hi:
        raise ValueError(f"{param.upper()} reading {value} is outside plausible range ({lo}–{hi}).")

def is_too_low(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is below its configured "too low" threshold
    defined in `config.TOO_LOW_THRESHOLDS`.

    Args:
        param (str): The name of the parameter.
        value (float): The numeric reading of the parameter.

    Returns:
        bool: True if `value` is strictly less than the threshold (and a
              threshold is defined for `param`), False otherwise.
    """
    thresh = TOO_LOW_THRESHOLDS.get(param)
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is above its configured "too high" threshold
    defined in `config.TOO_HIGH_THRESHOLDS`.

    Args:
        param (str): The name of the parameter.
        value (float): The numeric reading of the parameter.

    Returns:
        bool: True if `value` is strictly greater than the threshold (and a
              threshold is defined for `param`), False otherwise.
    """
    thresh = TOO_HIGH_THRESHOLDS.get(param)
    return thresh is not None and value > thresh

def is_out_of_range(
    param: str,
    value: Any,
    *,
    tank_id: int,
    ph: Optional[float] = None,
    temp_c: Optional[float] = None,
    test_time: Optional[time] = None,
) -> bool:
    """
    Determines if a parameter's value is outside the safe range configured for a specific tank.

    This function operates in the following order:
    1.  **Special Handling for Ammonia:** If `param` is "ammonia" and both `ph` and `temp_c` are provided,
        it calculates the toxic unionized NH₃ fraction using `nh3_fraction` and checks it against
        `TOO_HIGH_THRESHOLDS["ammonia"]`.
    2.  **Special Handling for CO₂ Indicator:** If `param` is "co2_indicator", it checks if the
        categorical `value` is anything other than "Green" (the ideal state). Additionally,
        if `value` is "Blue" (low CO2) and `test_time` is provided, it suppresses the warning
        if the test time falls outside the tank's custom CO2 schedule or the global default.
    3.  **Custom Range Lookup:** For other numeric parameters, it attempts to retrieve a user-defined
        custom safe range for the `tank_id` from `CustomRangeRepository`.
    4.  **Global Safe Range Fallback:** If no custom range is found, it falls back to the global
        `SAFE_RANGES` defined in `config.py`.
    5.  **Numeric Comparison:** Finally, it compares the `value` (which can be a `float` or a `pd.Series`)
        against the determined `(low, high)` safe range.

    Args:
        param (str): The name of the parameter (e.g., "ammonia", "ph", "co2_indicator").
        value (Any): The measured value of the parameter. This can be a `float` for numeric
                     parameters, a `pd.Series` when processing multiple values (e.g., a DataFrame column),
                     or a `str` for categorical parameters like "co2_indicator".
        tank_id (int): The ID of the tank, used to retrieve any custom safe ranges.
        ph (Optional[float]): The pH value. This is **required** if `param` is "ammonia"
                              for the unionized ammonia calculation. Defaults to `None`.
        temp_c (Optional[float]): The temperature in Celsius. This is **required** if `param`
                                  is "ammonia" for the unionized ammonia calculation. Defaults to `None`.
        test_time (Optional[time]): The time of the water test. Used for time-based CO2 warning suppression.
                                    Defaults to `None`.

    Returns:
        bool: True if the value is outside the safe range (or `co2_indicator` is not "Green`),
              False otherwise. Returns `False` if calculations fail, no safe range is defined,
              or the value cannot be converted to a float for numeric checks.
    """

    # Special-case handling for unionized ammonia, which depends on pH and temperature.
    if param == "ammonia" and ph is not None and temp_c is not None and value is not None:
        try:
            nh3 = nh3_fraction(float(value), ph, temp_c)
            if isinstance(nh3, pd.Series):
                return nh3.gt(TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)).any()
            return nh3 > TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)
        except (TypeError, ValueError):
            return False

    # Special-case handling for CO₂ indicator, which is categorical (color-based).
    if param == "co2_indicator":
        if isinstance(value, pd.Series):
            return (~value.eq("Green")).any()
        if isinstance(value, str):
            if value == "Blue":
                if test_time:
                    tank_repo = TankRepository()
                    tank_info = tank_repo.get_by_id(tank_id)
                    
                    custom_on_hour = tank_info.get("co2_on_hour") if tank_info else None
                    custom_off_hour = tank_info.get("co2_off_hour") if tank_info else None

                    # Determine schedule to use: custom if both are set, otherwise global default
                    if custom_on_hour is not None and custom_off_hour is not None:
                        on_hour_start, on_hour_end = custom_on_hour, custom_off_hour
                    else:
                        on_hour_start, on_hour_end = CO2_ON_SCHEDULE
                    
                    current_hour = test_time.hour

                    is_on_period = False
                    if on_hour_start <= on_hour_end:
                        # Period does NOT span midnight (e.g., 9 to 17)
                        is_on_period = (on_hour_start <= current_hour < on_hour_end)
                    else:
                        # Period DOES span midnight (e.g., 22 to 6)
                        is_on_period = (on_hour_start <= current_hour or current_hour < on_hour_end)
                    
                    if not is_on_period:
                        return False # Suppress warning
                return value != "Green"
            elif value == "Yellow":
                return True # Yellow (high) is always a warning
        return False

    custom_range_repo = CustomRangeRepository()
    custom = custom_range_repo.get(tank_id, param)
    
    lo, hi = custom if custom else SAFE_RANGES.get(param, (None, None))
    if lo is None or hi is None:
        return False

    if isinstance(value, pd.Series):
        return (value.lt(lo) | value.gt(hi)).any()

    try:
        val = float(value)
        return val < lo or val > hi
    except (TypeError, ValueError):
        return False