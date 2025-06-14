from typing import Optional
import pandas as pd
import streamlit as st
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS

# Use the database layer from aqualog_db
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
    """Shows a warning toast notification."""
    st.toast("⚠️ Check the **Warnings** tab for full details.")


def _build_banner_details(p: str, v: float, lo: float, hi: float) -> str:
    """Helper to construct banner details for out-of-range parameters."""
    if v < lo:
        plan = LOW_ACTION_PLANS.get(p, ["No plan available."])
        return f"- **{p.upper()}**: is too low ({v} < {lo}); " + "; ".join(plan)
    plan = ACTION_PLANS.get(p, ["No plan available."])
    return f"- **{p.upper()}**: is too high ({v} > {hi}); " + "; ".join(plan)


def show_out_of_range_banner(key_suffix: str = "") -> None:
    """Displays a simplified warning banner for out-of-range parameters."""
    suffix = f"_{key_suffix}" if key_suffix else ""
    hide_key = f"hide_banner{suffix}"

    if st.session_state.get(hide_key):
        if st.button("Show Warnings", key=f"show{suffix}"):
            st.session_state[hide_key] = False
            request_rerun()
        return

    latest = get_latest_test()
    if not latest:
        return

    breaches = []

    for p, (default_lo, default_hi) in SAFE_RANGES.items():
        v = latest.get(p)
        if v is None:
            continue

        if is_out_of_range(p, v, tank_id=latest.get("tank_id"),
                           ph=latest.get("ph"), temp_c=latest.get("temperature")):
            breaches.append(p.title().replace("_", " "))

    if breaches:
        date_str = pd.to_datetime(latest.get("date")).strftime("%Y-%m-%d") if latest.get("date") else "N/A"
        msg = f"⚠️ Latest test ({date_str}) out-of-range: {', '.join(breaches)}."
        msg += "\n\nCheck the **Warnings** tab for details."
        st.warning(msg)
        if st.button("Dismiss", key=f"dismiss{suffix}"):
            st.session_state[hide_key] = True
            request_rerun()


def show_parameter_advice(param: str, value: float) -> None:
    """Shows advice for a parameter based on its value."""
    lo_hi = SAFE_RANGES.get(param)
    if not lo_hi:
        return

    lo, hi = lo_hi
    if value < lo:
        st.warning(f"⚠️ {param.upper()} is too LOW "
                   f"({format_with_units(value, param)}). Recommended:")
        for line in LOW_ACTION_PLANS.get(param, ["No plan available."]):
            st.write(f"- {line}")
        return

    if value > hi:
        st.error(f"❗ {param.upper()} is too HIGH "
                 f"({format_with_units(value, param)}). Recommended:")
        for line in ACTION_PLANS.get(param, ["No plan available."]):
            st.write(f"- {line}")
        return

    st.success(
        f"{param.upper()} ({format_with_units(value, param)}) "
        f"is within safe range ({lo}–{hi})."
    )
