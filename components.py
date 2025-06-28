# components.py

"""
components.py – Reusable UI Components

A collection of shared, reusable Streamlit UI components for the AquaLog
dashboard. Provides standardized widgets and display elements like styled data
tables or warning cards to ensure a consistent look and feel across tabs.
"""

from __future__ import annotations # Added for type hinting consistency

import streamlit as st
import pandas as pd
from pandas.io.formats.style import Styler
from datetime import date, timedelta
from config import LOW_ACTION_PLANS, ACTION_PLANS

# Dictionary containing tooltip messages for each water parameter input
# in the sidebar's water test form. These provide users with quick
# contextual information and ideal ranges for each parameter.
tooltips: dict[str, str] = {
    "temperature": "Water temperature in °C (ideal: 22–26 °C).",
    "pH":          "Acidity/alkalinity (ideal: 6.5–7.6).",
    "ammonia":     "NH₃/NH₄⁺ (should be 0 ppm); toxicity depends on pH & temp.",
    "nitrite":     "NO₂⁻ (should be 0 ppm).",
    "nitrate":     "NO₃⁻ (ideal: 5–30 ppm for planted tanks).",
    "kh":          "Carbonate Hardness in dKH (ideal: 3–5 dKH).",
    "gh":          "General Hardness in °dH (ideal: 3–8 °dH).",
    "co2":         "CO₂ indicator color: Green=OK, Blue=low, Yellow=high."
}


def display_parameter_warning(param: str, value: float, safe_range: tuple, is_low: bool) -> None:
    """
    Displays a structured and detailed warning card for an out-of-range parameter.
    The card indicates if the parameter is too low or too high and suggests
    recommended action plans.

    Args:
        param (str): The name of the parameter (e.g., "ammonia", "ph").
        value (float): The measured value of the parameter.
        safe_range (tuple): A tuple `(low, high)` indicating the acceptable
                            safe range for the parameter.
        is_low (bool): A boolean indicating if the value is too low (`True`)
                       or too high (`False`).
    """
    param_name = param.replace("_", " ").title()
    low_val, high_val = safe_range
    
    if is_low:
        st.warning(f"Low {param_name} Detected")
    else:
        st.error(f"High {param_name} Detected")
        
    st.metric(
        label=f"Measured {param_name}",
        value=f"{value:.2f}",
        delta=f"Safe Range: {low_val} - {high_val}",
        delta_color="off" # 'off' color makes it gray, indicating a reference not a change
    )
    
    # Retrieve the appropriate action plan based on whether the value is too low or too high.
    action_plan = LOW_ACTION_PLANS.get(param) if is_low else ACTION_PLANS.get(param)
    if action_plan:
        st.markdown("**Recommended Actions:**")
        for step in action_plan:
            st.write(f"• {step}")

    st.markdown("---")


def display_metric_card(param: str, value: float, count: int, safe_ranges: dict[str, tuple[float, float]]) -> None: # Refined safe_ranges type
    """
    Displays a Streamlit metric card for a given water parameter.

    The card presents the parameter's current or average value, the number of
    readings considered, and visually indicates if the value is within the
    defined safe range using color.

    Args:
        param (str): The name of the parameter (e.g., "ph", "nitrate").
        value (float): The current or average value of the parameter.
        count (int): The number of readings contributing to the value.
        safe_ranges (dict[str, tuple[float, float]]): A dictionary containing safe ranges for parameters,
                                                 where keys are parameter names and values are (low, high) tuples.
    """
    lo, hi = safe_ranges.get(param, (None, None))
    # Determine if the value is within the safe range.
    within = lo is not None and hi is not None and lo <= value <= hi
    
    # Format label for display (e.g., "KH", "pH", "Ammonia").
    label = param.upper() if param in ("kh", "gh") else param.capitalize()
    
    # Add units if available.
    unit = "°dH" if param == "gh" else "dKH" if param == "kh" else ""
    
    st.metric(
        label=f"{label} {unit}".strip(),
        value=f"{value:.2f}",
        delta=f"{count} readings",
        delta_color="normal" if within else "inverse" # Green for normal, red for out-of-range
    )


def _highlight(v: float, lo: float, hi: float) -> str:
    """
    Helper function to determine the CSS style for a DataFrame cell based on
    its numerical value being outside a specified safe range.

    Args:
        v (float): The numerical value of the cell.
        lo (float): The lower bound of the safe range.
        hi (float): The upper bound of the high range.

    Returns:
        str: A CSS string for `background-color: red; color: white;` if the
             value is out of range, otherwise an empty string.
    """
    if lo is None or hi is None or pd.isna(v):
        return ""
    return "background-color: red; color: white;" if (v < lo or v > hi) else ""


def highlight_out_of_range(df: pd.DataFrame, safe_ranges: dict[str, tuple[float, float]]) -> Styler: # Refined safe_ranges type
    """
    Applies conditional styling to a Pandas DataFrame to visually highlight
    cells with numerical values that fall outside their defined safe ranges.

    Args:
        df (pd.DataFrame): The input Pandas DataFrame to style.
        safe_ranges (dict[str, tuple[float, float]]): A dictionary where keys are parameter names (expected
                                                 as column names in the DataFrame) and values are
                                                 tuples `(low_safe_value, high_safe_value)`.

    Returns:
        Styler: A Pandas Styler object with the applied highlighting, ready for
                rendering in Streamlit using `st.dataframe`.
    """
    styler = df.style
    for param, (lo, hi) in safe_ranges.items():
        if param in df.columns:
            # Apply the _highlight function to the specific column
            styler = styler.map(
                lambda v, lo=lo, hi=hi: _highlight(v, lo, hi),
                subset=[param]
            )
    return styler


def date_range_selector(label: str) -> tuple[str, str]:
    """
    Renders a Streamlit date input widget, allowing the user to select a date range.

    The widget defaults to displaying the last 30 days from the current date.

    Args:
        label (str): The label to display for the date input widget.

    Returns:
        tuple[str, str]: A tuple containing the selected start date and end date
                         as ISO formatted strings (`YYYY-MM-DD`).
    """
    today = date.today()
    default_start = today - timedelta(days=30)
    selection = st.date_input(label, [default_start, today])
    
    if isinstance(selection, (list, tuple)) and len(selection) == 2:
        start_date, end_date = selection
    else:
        # Fallback if only one date is selected or input is cleared
        start_date = default_start
        end_date = today
        
    return start_date.isoformat(), end_date.isoformat()