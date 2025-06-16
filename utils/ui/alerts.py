# utils/ui/alerts.py (Updated)

from typing import Optional, Dict, Any
import pandas as pd
import streamlit as st
from datetime import datetime
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
# 1. Import repositories instead of legacy functions
from aqualog_db.repositories import WaterTestRepository, CustomRangeRepository
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


def show_toast(title: str, message: str):
    """
    Displays a toast notification with a title and message.
    
    Args:
        title (str): The title of the toast notification (will be bold).
        message (str): The body content of the toast notification.
    """
    st.toast(f"**{title}**\n\n{message}")



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


# ─────────────────────────────────────────────────────────────────────────────
# Out-of-range banner — ***DISABLED***
# ─────────────────────────────────────────────────────────────────────────────
def show_out_of_range_banner(*_args, **_kwargs) -> None:
    """
    This banner has been temporarily disabled to avoid runtime issues.
    Callers can safely import & call it, but it now does nothing.
    
    NOTE: The internal logic has been refactored to use modern repositories
    so it can be re-enabled safely in the future.
    """
    return  # ← no-op

    # Example of refactored logic:
    # tank_id = st.session_state.get("tank_id")
    # if not tank_id:
    #     return
    #
    # water_test_repo = WaterTestRepository()
    # latest_test = water_test_repo.get_latest_for_tank(tank_id)
    #
    # if not latest_test:
    #     return
    #
    # warnings = []
    # for param, value in latest_test.items():
    #     if value is None or param in ['id', 'date', 'tank_id', 'notes']:
    #         continue
    #
    #     if is_out_of_range(param, value, tank_id=tank_id):
    #         custom_range_repo = CustomRangeRepository()
    #         low, high = custom_range_repo.get(tank_id, param) or SAFE_RANGES.get(param, (0,0))
    #         warnings.append(_build_banner_details(param, value, low, high))
    #
    # if warnings:
    #     st.warning("Issues in latest test:\n" + "\n".join(warnings))


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
