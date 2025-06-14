# utils/__init__.py
"""
utils — Main utility package for AquaLog
"""

# ─────────────────────────────────────────────────────────────────────────────
# UI utilities (alerts and rerun)
# ─────────────────────────────────────────────────────────────────────────────
from .ui.alerts import request_rerun, show_toast, show_out_of_range_banner, show_parameter_advice

# ─────────────────────────────────────────────────────────────────────────────
# Charting functions
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
from charts import clean_numeric_df, rolling_summary, multi_param_line_chart
__all__ = [
    # core
    "cache_data",
    # localization
    "is_mobile", "translate", "convert_value", "format_with_units",
    # validation
    "validate_reading", "is_too_low", "is_too_high", "is_out_of_range",
    # chemistry
    "nh3_fraction", "calculate_alkaline_buffer_dose", "calculate_equilibrium_dose",
    # database
    "BaseRepository",
    # UI
    "request_rerun", "show_toast", "show_out_of_range_banner", "show_parameter_advice",
    # charts
    "clean_numeric_df", "rolling_summary", "multi_param_line_chart",
]
