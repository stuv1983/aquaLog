from typing import Any, Optional
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS
from utils.chemistry import nh3_fraction
from aqualog_db.repositories.custom_range import CustomRangeRepository

HARD_LIMITS = {
    "ph": (0.0, 14.0),
    "ammonia": (0.0, 10.0),
    "nitrite": (0.0, 5.0),
    "nitrate": (0.0, 200.0),
    "temperature": (0.0, 40.0),
    "kh": (0.0, 30.0),
    "gh": (0.0, 30.0),
}


def validate_numeric(val: Any) -> Optional[float]:
    """
    Convert input to float if possible, otherwise return None.
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def is_out_of_range(param: str, value: float, tank_id: int | None = None) -> tuple[bool, bool, tuple[float, float]]:
    """
    Check if a parameter value is outside its safe range.
    Returns: (is_out, is_low, (low, high))
    """
    lo, hi = SAFE_RANGES.get(param, (None, None))
    is_low, is_high = False, False

    if tank_id is not None:
        repo = CustomRangeRepository()
        custom = repo.get_custom_range(param, tank_id)
        if custom:
            lo, hi = custom

    if lo is not None and value < lo:
        is_low = True
    if hi is not None and value > hi:
        is_high = True

    return (is_low or is_high), is_low, (lo, hi)