# utils/ui/alerts.py

"""
alerts.py – UI Alert Components

Provides UI-specific helper functions for displaying alerts and notifications to
the user. Includes functions for showing toast messages, formatted parameter
advice cards, and a prominent banner for out-of-range water test results.
"""

from __future__ import annotations # Already present, ensuring consistency

from typing import Optional, Any
import streamlit as st
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS

# FIXED: Corrected the relative import paths for both validation and localization
from ..validation import is_out_of_range
from ..localization import format_with_units

# Import WaterTestRecord TypedDict
from aqualog_db.repositories.water_test import WaterTestRecord


def request_rerun() -> None:
    """
    Requests a Streamlit rerun using the most appropriate API available.

    This function abstracts away differences between Streamlit versions
    (`st.rerun`, `st.experimental_rerun`, `st.experimental_request_rerun`)
    to trigger a re-execution of the script, often used after state changes
    or database updates.
    """
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "experimental_request_rerun"):
        st.experimental_request_rerun()


def show_toast(title: str, message: str | None = None, *, icon: str | None = None) -> None:
    """
    Displays a toast notification at the bottom-right of the Streamlit app.

    Toasts are ephemeral messages used to provide quick feedback to the user
    without interrupting their workflow. The `title`, `message`, and `icon`
    are combined to form the toast's displayed body.

    Args:
        title (str): The main title text for the toast.
        message (str | None): An optional longer message to display below the title.
                               Defaults to `None`.
        icon (str | None): An optional emoji or icon identifier to display with the toast.
                           Defaults to `None`.

    Returns:
        None: This function displays a toast notification and does not return any value.
    """
    body = f"**{title}**"
    if message:
        body += f"\n\n{message}"
    
    st.toast(body, icon=icon)


def _build_banner_details(param: str, value: float, low: float, high: float) -> str:
    """
    Constructs a formatted string detailing an out-of-range parameter for
    inclusion in warning banners or detailed advice cards.

    This helper function is typically used internally by `show_out_of_range_banner`
    or similar functions to generate concise, Markdown-compatible summaries
    of parameter issues and their associated action plans. It incorporates
    the parameter name, its measured value, the safe range, and a brief
    summary of the action plan from `LOW_ACTION_PLANS` or `ACTION_PLANS`.

    Args:
        param (str): The name of the parameter (e.g., "ph", "ammonia").
        value (float): The measured value of the parameter.
        low (float): The safe low threshold for the parameter.
        high (float): The safe high threshold for the parameter.

    Returns:
        str: A formatted string describing the warning and recommended actions,
             suitable for Markdown display.
    """
    if value < low:
        # Get the action plan for too low values.
        plan = LOW_ACTION_PLANS.get(param, ["No plan available."])
        return (f"- **{param.upper()}**: Too low ({format_with_units(value, param)} < "
                f"{format_with_units(low, param)}); " + "; ".join(plan))
    
    # Get the action plan for too high values.
    plan = ACTION_PLANS.get(param, ["No plan available."])
    return (f"- **{param.upper()}**: Too high ({format_with_units(value, param)} > "
            f"{format_with_units(high, param)}); " + "; ".join(plan))


def show_out_of_range_banner(*_args: Any, **_kwargs: Any) -> None:
    """
    Displays a persistent warning banner at the top of the main content area
    if the most recent water test for the selected tank has any parameters
    that are outside their configured safe ranges.

    This function dynamically imports `WaterTestRepository` and `is_out_of_range`
    locally to avoid circular import issues in the application's module structure.
    The banner directs users to the 'Warnings' tab for detailed advice.

    Note: `*_args` and `**_kwargs` are used here to accept any extra arguments
          without using them, making the function signature flexible for various
          Streamlit call contexts or potential future extensions. They are not
          directly processed by this function.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    # Import WaterTestRepository locally to break a potential circular dependency.
    from aqualog_db.repositories import WaterTestRepository
    # Import is_out_of_range locally as it's part of the core logic to check status.
    from utils.validation import is_out_of_range

    # Get the currently selected tank ID from Streamlit's session state.
    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        return # Do nothing if no tank is selected.

    repo = WaterTestRepository()
    latest_test: Optional[WaterTestRecord] = repo.get_latest_for_tank(tank_id) # Explicitly type latest_test

    if not latest_test:
        return # Do nothing if no water test data is available for the tank.

    out_of_range_found = False
    
    # Define the relevant parameters to check for out-of-range values.
    relevant_params = ["ph", "ammonia", "nitrite", "nitrate", "temperature", "kh", "gh", "co2_indicator"]

    # Iterate through parameters to check if any are out of range.
    for param in relevant_params:
        value = latest_test.get(param)
        if value is not None:
            # Call the validation utility function to check if the parameter is out of range.
            if is_out_of_range(
                param,
                value,
                tank_id=tank_id, # Pass tank_id for custom range lookup
                ph=latest_test.get("ph"),       # Pass pH for ammonia calculation
                temp_c=latest_test.get("temperature") # Pass temperature for ammonia calculation
            ):
                out_of_range_found = True
                break # A single out-of-range parameter is enough to show the banner.

    if out_of_range_found:
        # Display the Streamlit warning banner.
        st.warning(
            "⚠️ The most recent water test has out-of-range parameters. "
            "Check the 'Warnings' tab for details.",
            icon="❗" # Display an exclamation icon.
        )


def show_parameter_advice(param: str, value: float) -> None:
    """
    Displays a formatted advice card for a single water parameter.

    This card indicates whether the parameter is too low, too high, or
    within the safe range (using `config.SAFE_RANGES`), and provides specific
    action plans (from `config.LOW_ACTION_PLANS` or `config.ACTION_PLANS`)
    if it's out of range.

    Args:
        param (str): The name of the parameter (e.g., "ph", "nitrate").
        value (float): The measured value of the parameter.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    if param not in SAFE_RANGES:
        st.warning(f"Unknown parameter: {param}")
        return
        
    low, high = SAFE_RANGES[param] # Get the global safe range for context.
    formatted_value = format_with_units(value, param) # Get value formatted with units.
    
    if value < low:
        # Display a warning container for low values.
        with st.container(border=True):
            st.warning(f"⚠️ {param.upper()} is too LOW ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            # List action plan steps.
            for line in LOW_ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    if value > high:
        # Display an error container for high values.
        with st.container(border=True):
            st.error(f"❗ {param.upper()} is too HIGH ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            # List action plan steps.
            for line in ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    # Display a success message if the parameter is within the safe range.
    st.success(
        f"✓ {param.upper()} ({formatted_value}) is within safe range "
        f"({format_with_units(low, param)}–{format_with_units(high, param)})",
        icon="✓"
    )