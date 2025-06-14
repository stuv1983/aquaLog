'''utils/__init__.py: Aggregator for all utility modules'''  
# Core helpers  
from .core import is_mobile, get_viewport_width  

# Chemistry calculations  
from .chemistry import calc_unionized_ammonia, adjust_ph  

# Database connection utilities  
from .database import get_connection, execute_query  

# Localization and formatting  
from .localization import translate, format_with_units  

# Validation routines  
from .validation import validate_ph, validate_nitrate, validate_ammonia  

# UI utilities (alerts and rerun)  
from .ui.alerts import request_rerun, show_toast, show_out_of_range_banner, show_parameter_advice  

# Charting functions  
from .ui.charts import clean_numeric_df, rolling_summary, multi_param_line_chart
