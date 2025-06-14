# utils/validation.py

from typing import Any, Optional
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS
from aqualog_db.repositories.custom_range import get_custom_range
from utils.chemistry import nh3_fraction

HARD_LIMITS = {
    "temperature": (0.0, 40.0),
    "ph":          (0.0, 14.0),
    "ammonia":     (0.0, 10.0),
    "nitrite":     (0.0, 10.0),
    "nitrate":     (0.0, 500.0),
    "kh":          (0.0, 20.0),
    "gh":          (0.0, 30.0),
}

def validate_reading(param: str, value: float) -> None:
    """
    Validates that a reading is within hard physical limits.
    """
    if param not in HARD_LIMITS:
        return
    lo, hi = HARD_LIMITS[param]
    if value < lo or value > hi:
        raise ValueError(f"{param.upper()} reading {value} is outside plausible range ({lo}–{hi}).")

def is_too_low(param: str, value: float) -> bool:
    """
    Checks if a value is below the too-low threshold for a parameter.
    """
    thresh = TOO_LOW_THRESHOLDS.get(param)
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    """
    Checks if a value is above the too-high threshold for a parameter.
    """
    thresh = TOO_HIGH_THRESHOLDS.get(param)
    return thresh is not None and value > thresh

def is_out_of_range(
    param: str,
    value: Any,
    *,
    tank_id: int,
    ph: Optional[float] = None,
    temp_c: Optional[float] = None
) -> bool:
    """
    Determines if a value is outside its safe range, considering custom ranges.
    """
    if param == "ammonia" and ph is not None and temp_c is not None and isinstance(value, (int, float)):
        return nh3_fraction(value, ph, temp_c) > TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)
    
    if param == "co2_indicator":
        return isinstance(value, str) and value != "Green"

    custom_range = get_custom_range(tank_id, param)
    lo, hi = (custom_range if custom_range else SAFE_RANGES.get(param, (None, None)))

    if lo is None or hi is None:
        return False
    if isinstance(value, (int, float)):
        return value < lo or value > hi
    return False
