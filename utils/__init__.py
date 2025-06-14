# utils/__init__.py
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
from .localization import is_mobile, translate, convert_value, format_with_units

# ─────────────────────────────────────────────────────────────────────────────
# Validation routines
# ─────────────────────────────────────────────────────────────────────────────
from .validation import validate_reading, is_too_low, is_too_high, is_out_of_range

# ─────────────────────────────────────────────────────────────────────────────
# Chemistry calculations
# ─────────────────────────────────────────────────────────────────────────────
from .chemistry import nh3_fraction, calculate_alkaline_buffer_dose, calculate_equilibrium_dose

# ─────────────────────────────────────────────────────────────────────────────
# Database utilities
# ─────────────────────────────────────────────────────────────────────────────
from .database import get_connection, ensure_custom_ranges_schema, ensure_water_tests_schema

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# UI utilities (alerts and rerun)
# ─────────────────────────────────────────────────────────────────────────────
from .alerts import request_rerun, show_toast, show_out_of_range_banner, show_parameter_advice

# ─────────────────────────────────────────────────────────────────────────────
# Charting functions
# ─────────────────────────────────────────────────────────────────────────────
from .charts import clean_numeric_df, rolling_summary, multi_param_line_chart
