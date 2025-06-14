"""
utils/__init__.py – Consolidated utility imports for external modules.
Refactored: 2025-06-14
"""

# Core functions
from .core import (
    cache_data,
    clear_cache,
    is_mobile,
    load_config,
)

# Localization / unit conversion
from .localization import (
    translate,
    format_with_units,
    convert_temperature,
    convert_volume,
)

# Validation
from .validation import (
    validate_parameter_value,
    is_out_of_range,
)

# Chemistry
from .chemistry import (
    nh3_fraction,
    calculate_equilibrium_dose,
    calculate_alkaline_buffer_dose,
)

# UI elements
from .ui.alerts import (
    show_out_of_range_banner,
    show_success_banner,
)
from .ui.charts import (
    plot_trend_chart,
    plot_correlation_heatmap,
)

# Database helper aliases for legacy support (refactored)
from aqualog_db.repositories.water_test import (
    get_latest_test,
    get_most_recent_value,
)
from aqualog_db.repositories.custom_range import (
    get_custom_range,
)
