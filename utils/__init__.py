"""
utils — Main utility package for AquaLog
"""

# ─────────────────────────────────────────────────────────────────────────────
# Core utilities
# ─────────────────────────────────────────────────────────────────────────────
from .core import cache_data

# ─────────────────────────────────────────────────────────────────────────────
# Localization & unit conversion
# ─────────────────────────────────────────────────────────────────────────────
from .localization import (
    is_mobile,
    translate,
    convert_value,
    format_with_units,
)

# ─────────────────────────────────────────────────────────────────────────────
# Validation & Data-frame helpers
# ─────────────────────────────────────────────────────────────────────────────
from .validation import (        # ← arrow_safe is part of validation.py
    validate_reading,
    is_too_low,
    is_too_high,
    is_out_of_range,
    arrow_safe,                    # 🔸 Arrow-compatibility helper
)

# ─────────────────────────────────────────────────────────────────────────────
# Chemistry calculations
# ─────────────────────────────────────────────────────────────────────────────
from .chemistry import (
    nh3_fraction,
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
    calculate_fritzzyme7_dose, # FIX: Added the new dosing function
)

# ─────────────────────────────────────────────────────────────────────────────
# Database utilities
# ─────────────────────────────────────────────────────────────────────────────
from aqualog_db.base import BaseRepository

# ─────────────────────────────────────────────────────────────────────────────
# UI utilities (alerts and rerun)
# ─────────────────────────────────────────────────────────────────────────────
from .ui.alerts import (
    request_rerun,
    show_toast,
    show_out_of_range_banner,
    show_parameter_advice,
)

# ─────────────────────────────────────────────────────────────────────────────
# Charting functions
# ─────────────────────────────────────────────────────────────────────────────
from .ui.charts import (
    clean_numeric_df,
    rolling_summary,
    multi_param_line_chart,
)

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
__all__ = [
    # core
    "cache_data",
    # localization
    "is_mobile",
    "translate",
    "convert_value",
    "format_with_units",
    # validation / df helpers
    "validate_reading",
    "is_too_low",
    "is_too_high",
    "is_out_of_range",
    "arrow_safe",                        # ← now publicly exposed
    # chemistry
    "nh3_fraction",
    "calculate_alkaline_buffer_dose",
    "calculate_equilibrium_dose",
    "calculate_fritzzyme7_dose", # FIX: Added the new dosing function
    # database
    "BaseRepository",
    # UI utilities
    "request_rerun",
    "show_toast",
    "show_out_of_range_banner",
    "show_parameter_advice",
    # charts
    "clean_numeric_df",
    "rolling_summary",
    "multi_param_line_chart",
]