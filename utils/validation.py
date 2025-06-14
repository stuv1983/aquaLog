# utils/validation.py

from typing import Any, Optional
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS
from db import get_custom_range
from .chemistry import nh3_fraction

# Hard physical limits for parameter sanity checks
HARD_LIMITS: dict[str, tuple[float, float]] = {
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
    Raises ValueError if `value` sits outside globally plausible limits for `param`.
    """
    limits = HARD_LIMITS.get(param)
    if not limits:
        return
    lo, hi = limits
    if value < lo or value > hi:
        raise ValueError(f"{param.upper()} reading {value} is outside plausible range ({lo}–{hi}).")

def is_too_low(param: str, value: float) -> bool:
    """
    Returns True if `value` < the configured TOO_LOW_THRESHOLDS for `param`.
    """
    thresh = TOO_LOW_THRESHOLDS.get(param)
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    """
    Returns True if `value` > the configured TOO_HIGH_THRESHOLDS for `param`.
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
    Checks `value` against the safe range for `param`, using either global SAFE_RANGES
    or per-tank custom ranges (via `get_custom_range`), and special NH₃ logic.
    """
    # If ammonia, compute unionized NH₃ toxicity instead
    if param == "ammonia" and ph is not None and temp_c is not None and isinstance(value, (int, float)):
        return nh3_fraction(value, ph, temp_c) > TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)

    # CO2 indicator is out-of-range if not exactly "Green"
    if param == "co2_indicator":
        return isinstance(value, str) and value != "Green"

    # Look for a user-defined custom range first
    custom = get_custom_range(tank_id, param)
    lo, hi = custom if custom else SAFE_RANGES.get(param, (None, None))

    # If we don’t have valid boundaries, we can’t flag it
    if lo is None or hi is None:
        return False

    # Finally, for numeric types check below/above
    if isinstance(value, (int, float)) and (value < lo or value > hi):
        return True

    return False
