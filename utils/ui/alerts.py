# utils/ui/alerts.py

"""
alerts.py – UI Alert Components

Provides UI-specific helper functions for displaying alerts and notifications to
the user. Includes functions for showing toast messages and formatted parameter
advice cards.
"""

from typing import Optional
import streamlit as st
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS

# FIXED: Corrected the relative import paths for both validation and localization
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


def show_toast(title: str, message: str | None = None, *, icon: str | None = None):
    """
    Displays a toast notification with a title, optional message, and optional icon.
    """
    body = f"**{title}**"
    if message:
        body += f"\n\n{message}"
    
    st.toast(body, icon=icon)


def _build_banner_details(param: str, value: float, low: float, high: float) -> str:
    """Constructs formatted banner details for out-of-range parameters."""
    if value < low:
        plan = LOW_ACTION_PLANS.get(param, ["No plan available."])
        return (f"- **{param.upper()}**: Too low ({format_with_units(value, param)} < "
                f"{format_with_units(low, param)}); " + "; ".join(plan))
    
    plan = ACTION_PLANS.get(param, ["No plan available."])
    return (f"- **{param.upper()}**: Too high ({format_with_units(value, param)} > "
            f"{format_with_units(high, param)}); " + "; ".join(plan))


def show_out_of_range_banner(*_args, **_kwargs) -> None:
    """
    Re-enabled banner for out-of-range parameters.
    Since the original 'runtime issues' are not known, this version
    provides a general warning and directs to the Warnings tab.
    """
    # This function would ideally check actual data to determine if a banner is needed.
    # For now, as a re-enabled placeholder, it suggests checking the dedicated Warnings tab.
    st.warning("⚠️ Some water parameters might be out of range. Check the 'Warnings' tab for details.", icon="❗")


def show_parameter_advice(param: str, value: float) -> None:
    """Displays formatted advice for a parameter based on its value."""
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
