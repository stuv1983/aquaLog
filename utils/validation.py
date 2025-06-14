# utils/validation.py
import pandas as pd  
from typing import Any, Optional
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS
from aqualog_db.legacy import get_custom_range
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



def arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy whose ‘date’ column is true datetime64[ns] so
    Streamlit/Arrow can serialise it.  Call this once before st.dataframe()
    or Altair charts when the DF was NOT read via read_sql_query(parse_dates).
    """
    if "date" in df.columns and df["date"].dtype != "datetime64[ns]":
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


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
    temp_c: Optional[float] = None,
) -> bool:
    """
    Return True if *value* (scalar **or** Series / array) is outside the safe
    range for *param*.  Always collapses to a single Python bool, so callers
    can safely use `if is_out_of_range(...):`.
    """

    # ── Special-case unionised ammonia ────────────────────────────────────
    if param == "ammonia" and ph is not None and temp_c is not None:
        # Accept both scalar and vector values
        try:
            nh3 = nh3_fraction(value, ph, temp_c)         # may return Series
            if isinstance(nh3, pd.Series):
                return nh3.gt(TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)).any()
            return nh3 > TOO_HIGH_THRESHOLDS.get("ammonia", 0.02)
        except Exception:
            return False

    # ── CO₂ indicator is categorical ──────────────────────────────────────
    if param == "co2_indicator":
        if isinstance(value, pd.Series):
            return (~value.eq("Green")).any()
        return isinstance(value, str) and value != "Green"

    # ── Determine safe range (custom > global) ────────────────────────────
    custom = get_custom_range(tank_id, param)
    lo, hi = custom if custom else SAFE_RANGES.get(param, (None, None))
    if lo is None or hi is None:
        return False

    # ── Numeric checks – handle scalar & vector uniformly ─────────────────
    if isinstance(value, pd.Series):
        return (value.lt(lo) | value.gt(hi)).any()

    try:
        val = float(value)
        return val < lo or val > hi
    except (TypeError, ValueError):
        return False
