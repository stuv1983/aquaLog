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

# Default suggestions for out-of-range water parameters
# Updated to recommend pure nitrifier products instead of Prime/Stability
default_suggestions = {
    "ammonia": {
        "high": (
            "- Perform a 50% water change immediately.\n"
            "- Seed with nitrifying bacteria (e.g., FritzZyme TurboStart 700 or FritzZyme 7, Tetra SafeStart+).\n"
            "- Stop feeding until ammonia levels stabilize.\n"
            "- Increase oxygenation (air stones, powerheads).\n"
            "- Monitor ammonia and nitrite levels daily; consider adding bio-media."
        )
    },
    "nitrite": {
        "high": (
            "- Perform a 30–50% water change immediately.\n"
            "- Seed with nitrifying bacteria (e.g., FritzZyme TurboStart 700 or FritzZyme 7, Tetra SafeStart+).\n"
            "- Run air stones 24/7 to boost oxygen.\n"
            "- Check filter bio-media is intact; avoid cleaning too aggressively.\n"
            "- Monitor nitrite and ammonia daily to track cycle progress."
        )
    },
    "nitrate": {
        "high": (
            "- Perform a 30–50% water change to reduce nitrates.\n"
            "- Reduce feeding frequency and quantity.\n"
            "- Add fast-growing plants to consume excess nitrates.\n"
            "- Check fertilizer dosing to avoid over-enrichment.\n"
            "- Vacuum substrate to remove decaying debris."
        )
    },
    "pH": {
        "low": (
            "- Dose Alkaline Buffer: 1 level teaspoon (≈5 g) per 76 L to raise pH/KH by ≈0.3.\n"
            "- Repeat daily until pH reaches 6.5–7.6.\n"
            "- Add in small increments; avoid sudden spikes.\n"
            "- If pH overshoots above 8.0, use Neutral Regulator."
        ),
        "high": (
            "- Dose Neutral Regulator: 1.25 mL per 3.8 L, wait 1 hour, retest; repeat until pH is 6.5–7.6.\n"
            "- Rinse substrate if leaching carbonate.\n"
            "- Avoid daily pH corrections unless fish are stressed."
        )
    },
    "kh": {
        "low": (
            "- Dose Alkaline Buffer: 1 level teaspoon (≈5 g) per 76 L daily until KH reaches 3–5 dKH.\n"
            "- Monitor KH every 24 hours; discontinue when stable.\n"
            "- For RO top-offs, remineralize with Alkaline Buffer."
        ),
        "high": (
            "- Stop buffering additives.\n"
            "- Use RO or soft water (mix tap and RO 1:1) for top-offs.\n"
            "- Allow plants to gradually consume carbonate hardness."
        )
    },
    "gh": {
        "low": (
            "- ⚠️ GH is low (below 3 °dH).\n"
            "- Add remineralizer (e.g., Seachem Equilibrium) per instructions.\n"
            "- Target a GH of 3–8 °dH; re-test and adjust as needed."
        ),
        "high": (
            "- ⚠️ GH is high (above 12 °dH).\n"
            "- Perform a partial water change with softer or RO water.\n"
            "- Avoid hard water supplements until GH drops into range.\n"
            "- Dilute with softer water sources as needed."
        )
    }
}

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
        # ** ERROR FIX: Removed the inner expander **
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
