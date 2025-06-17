# utils/__init__.py (Corrected)

"""
utils — Main utility package for AquaLog
"""

# Import is_mobile from core where it is now solely defined
from .core import cache_data, is_mobile
from .localization import (
    translate,
    convert_value,
    format_with_units,
)
from .validation import (
    validate_reading,
    is_too_low,
    is_too_high,
    is_out_of_range,
    arrow_safe,
)
from .chemistry import (
    nh3_fraction,
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
    calculate_fritzzyme7_dose,
)
from .ui.alerts import (
    request_rerun,
    show_toast,
    show_out_of_range_banner,
    show_parameter_advice,
)
from .ui.charts import (
    clean_numeric_df,
    rolling_summary,
    multi_param_line_chart,
)

__all__ = [
    # core
    "cache_data",
    "is_mobile",
    # localization
    "translate",
    "convert_value",
    "format_with_units",
    # validation / df helpers
    "validate_reading",
    "is_too_low",
    "is_too_high",
    "is_out_of_range",
    "arrow_safe",
    # chemistry
    "nh3_fraction",
    "calculate_alkaline_buffer_dose",
    "calculate_equilibrium_dose",
    "calculate_fritzzyme7_dose",
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