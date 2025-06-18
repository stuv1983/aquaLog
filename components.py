# components.py

"""
components.py – Reusable UI Components

A collection of shared, reusable Streamlit UI components for the AquaLog
dashboard. Provides standardized widgets and display elements like styled data
tables or warning cards to ensure a consistent look and feel across tabs.

"""

import streamlit as st
import pandas as pd
from pandas.io.formats.style import Styler
from datetime import date, timedelta
from config import LOW_ACTION_PLANS, ACTION_PLANS

# Tooltips for each parameter input in sidebar
tooltips = {
    "temperature": "Water temperature in °C (ideal: 22–26 °C).",
    "pH":          "Acidity/alkalinity (ideal: 6.5–7.6).",
    "ammonia":     "NH₃/NH₄⁺ (should be 0 ppm); toxicity depends on pH & temp.",
    "nitrite":     "NO₂⁻ (should be 0 ppm).",
    "nitrate":     "NO₃⁻ (ideal: 5–30 ppm for planted tanks).",
    "kh":          "Carbonate Hardness in dKH (ideal: 3–5 dKH).",
    "gh":          "General Hardness in °dH (ideal: 3–8 °dH).",
    "co2":         "CO₂ indicator color: Green=OK, Blue=low, Yellow=high."
}


def display_parameter_warning(param: str, value: float, safe_range: tuple, is_low: bool):
    """
    Displays a structured and detailed warning for an out-of-range parameter.
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
        delta_color="off"
    )
    
    action_plan = LOW_ACTION_PLANS.get(param) if is_low else ACTION_PLANS.get(param)
    if action_plan:
        st.markdown("**Recommended Actions:**")
        for step in action_plan:
            st.write(f"- {step}")

    st.markdown("---")


def display_metric_card(param: str, value: float, count: int, safe_ranges: dict):
    lo, hi = safe_ranges.get(param, (None, None))
    within = lo is not None and hi is not None and lo <= value <= hi
    label = param.upper() if param in ("kh", "gh") else param.capitalize()
    unit = "°dH" if param == "gh" else "dKH" if param == "kh" else ""
    st.metric(
        label=f"{label} {unit}".strip(),
        value=f"{value:.2f}",
        delta=f"{count} readings",
        delta_color="normal" if within else "inverse"
    )


def _highlight(v, lo, hi):
    if lo is None or hi is None or pd.isna(v):
        return ""
    return "background-color: red; color: white;" if (v < lo or v > hi) else ""


def highlight_out_of_range(df: pd.DataFrame, safe_ranges: dict) -> Styler:
    styler = df.style
    for param, (lo, hi) in safe_ranges.items():
        if param in df.columns:
            styler = styler.map(
                lambda v, lo=lo, hi=hi: _highlight(v, lo, hi),
                subset=[param]
            )
    return styler


def date_range_selector(label: str) -> tuple[str, str]:
    today = date.today()
    default_start = today - timedelta(days=30)
    selection = st.date_input(label, [default_start, today])
    if isinstance(selection, (list, tuple)) and len(selection) == 2:
        start_date, end_date = selection
    else:
        start_date = default_start
        end_date = selection
    return start_date.isoformat(), end_date.isoformat()