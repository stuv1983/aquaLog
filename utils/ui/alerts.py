from typing import Optional, Dict, Any
import pandas as pd
import streamlit as st
from datetime import datetime
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from aqualog_db.legacy import get_latest_test, get_custom_range
from ..validation import is_out_of_range
from ..localization import format_with_units

def request_rerun() -> None:
    """Requests a Streamlit rerun using the current API."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "experimental_request_rerun"):
        st.experimental_request_rerun()


def show_toast() -> None:
    """Shows a warning toast notification with consistent styling."""
    st.toast("⚠️ Check the **Warnings** tab for full details.", icon="⚠️")


def _build_banner_details(param: str, value: float, low: float, high: float) -> str:
    """Constructs formatted banner details for out-of-range parameters.
    
    Args:
        param: Parameter name (e.g., 'ph', 'ammonia')
        value: Measured parameter value
        low: Lower safe bound
        high: Upper safe bound
    
    Returns:
        Formatted warning message with action plan
    """
    if value < low:
        plan = LOW_ACTION_PLANS.get(param, ["No plan available."])
        return (f"- **{param.upper()}**: Too low ({format_with_units(value, param)} < "
                f"{format_with_units(low, param)}); " + "; ".join(plan))
    
    plan = ACTION_PLANS.get(param, ["No plan available."])
    return (f"- **{param.upper()}**: Too high ({format_with_units(value, param)} > "
            f"{format_with_units(high, param)}); " + "; ".join(plan))


def show_out_of_range_banner(key_suffix: str = "") -> None:
    """Displays a warning banner for out-of-range parameters with dismiss functionality.
    
    Args:
        key_suffix: Optional suffix for session state keys to support multiple instances
    """
    suffix = f"_{key_suffix}" if key_suffix else ""
    hide_key = f"hide_banner{suffix}"
    
    # Handle banner visibility toggle
    if st.session_state.get(hide_key, False):
        if st.button("Show Warnings", key=f"show{suffix}"):
            st.session_state[hide_key] = False
            request_rerun()
        return

    latest = get_latest_test()
    if not latest or not isinstance(latest, dict):
        return

    # Process parameter breaches
    breaches = []
    details = []
    tank_id = latest.get("tank_id", 0)
    
    for param, (default_low, default_high) in SAFE_RANGES.items():
        value = latest.get(param)
        if value is None:
            continue
            
        custom_range = get_custom_range(tank_id, param)
        low, high = custom_range if custom_range else (default_low, default_high)
        
        if is_out_of_range(param, value, tank_id=tank_id,
                          ph=latest.get("ph"), temp_c=latest.get("temperature")):
            breaches.append(param.title().replace("_", " "))
            details.append(_build_banner_details(param, value, low, high))

    # Display warning if breaches exist
    if breaches:
        try:
            test_date = latest.get("date")
            date_str = (pd.to_datetime(test_date).strftime("%Y-%m-%d") 
                       if test_date else "N/A")
        except (ValueError, TypeError):
            date_str = "N/A"
            
        with st.expander(f"⚠️ Latest test ({date_str}) warnings", expanded=True):
            st.warning(f"Out-of-range parameters: {', '.join(breaches)}")
            st.markdown("\n".join(details))
            
            if st.button("Dismiss", key=f"dismiss{suffix}"):
                st.session_state[hide_key] = True
                request_rerun()


def show_parameter_advice(param: str, value: float) -> None:
    """Displays formatted advice for a parameter based on its value.
    
    Args:
        param: Parameter name (e.g., 'ph', 'nitrate')
        value: Measured parameter value
    """
    if param not in SAFE_RANGES:
        st.warning(f"Unknown parameter: {param}")
        return
        
    low, high = SAFE_RANGES[param]
    formatted_value = format_with_units(value, param)
    
    if value < low:
        with st.container(border=True):
            st.warning(f"⚠️ {param.upper()} is too LOW ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in LOW_ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    if value > high:
        with st.container(border=True):
            st.error(f"❗ {param.upper()} is too HIGH ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    st.success(
        f"✓ {param.upper()} ({formatted_value}) is within safe range "
        f"({format_with_units(low, param)}–{format_with_units(high, param)})",
        icon="✓"
    )
