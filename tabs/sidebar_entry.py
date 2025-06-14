"""
tabs/sidebar_entry.py – Sidebar Water‐Test Form (v3.3.0)
Renders the “Log Water Test” UI in the sidebar with mobile and desktop layouts,
validates inputs, saves readings per tank, and displays out-of-range advice.
Updated: 2025-06-10
"""


import datetime                       # For timestamping test entries
from datetime import date            # For today's date input
import streamlit as st                # Streamlit UI components

from db import save_water_test         # Central DB helper (handles tank_id)
from config import (
    SAFE_RANGES,                      # Safe ranges per parameter
    ACTION_PLANS,                     # Advice for values above high threshold
    LOW_ACTION_PLANS,                 # Advice for values below low threshold
    is_too_low,                       # Returns True if value < safe min
    is_too_high                       # Returns True if value > safe max
)
from utils import (
    is_mobile,                        # Detect mobile/narrow viewport
    ensure_water_tests_schema,        # Ensure water_tests table exists and schema is up-to-date
    show_parameter_advice             # Display parameter-specific advice messages
)


def sidebar_entry():
    """
    Render the "Log Water Test" form in the sidebar.
    - Ensures water_tests schema exists (adds tank_id via ensure_water_tests_schema).
    - On mobile: groups inputs in an expander, Save button full-width.
    - On desktop: shows inputs directly in sidebar.
    - Validates inputs and saves via save_water_test(data, tank_id).
    - After saving, checks for out-of-range values and shows advice.

    Multi-tank support: uses st.session_state["tank_id"] (default=1).
    """
    st.sidebar.header("🔬 Log Water Test")

    # Ensure the water_tests table and its columns (including tank_id) exist
    ensure_water_tests_schema()

    # Tooltips for guidance
    tooltips = {
        "ph": "Ideal pH is 6.5–7.6 for most community tanks.",
        "ammonia": "Ammonia should be 0 ppm.",
        "nitrite": "Nitrite should be 0 ppm once cycling is complete.",
        "nitrate": "Nitrate should be 5–30 ppm for planted tanks.",
        "kh": "KH (carbonate hardness) ideal is 3–5 dKH.",
        "temperature": "Optimal temperature is 22–26 ℃.",
    }

    # Get active tank ID (fallback to 1 for legacy)
    tank_id = st.session_state.get("tank_id", 1)

    # ─────────────────────────────────────────────────────────────────────
    # Mobile layout: inputs inside expander
    # ─────────────────────────────────────────────────────────────────────
    if is_mobile():
        with st.sidebar.expander("Enter Test Details", expanded=True):
            # Date for the test (defaults to today, can adjust)
            date_in = st.date_input("Date", value=date.today(), key="test_date")

            # Numeric inputs
            ph = st.number_input(
                "pH", min_value=5.0, max_value=9.0, value=7.0,
                step=0.1, help=tooltips["ph"], key="ph_input"
            )
            temperature = st.number_input(
                "Temp (℃)", min_value=15.0, max_value=35.0, value=26.0,
                step=0.5, help=tooltips["temperature"], key="temp_input"
            )
            ammonia = st.number_input(
                "Ammonia (ppm)", min_value=0.0, max_value=8.0, value=0.0,
                step=0.1, help=tooltips["ammonia"], key="ammonia_input"
            )
            nitrite = st.number_input(
                "Nitrite (ppm)", min_value=0.0, max_value=5.0, value=0.0,
                step=0.1, help=tooltips["nitrite"], key="nitrite_input"
            )
            nitrate = st.number_input(
                "Nitrate (ppm)", min_value=0.0, max_value=80.0, value=5.0,
                step=1.0, help=tooltips["nitrate"], key="nitrate_input"
            )
            kh = st.number_input(
                "KH (dKH)", min_value=0.0, max_value=20.0, value=2.0,
                step=0.1, help=tooltips["kh"], key="kh_input"
            )

            # CO₂ indicator
            co2_indicator = st.selectbox(
                "CO₂ Ind.", ["", "Blue (Low)", "Green (Ideal)", "Yellow (High)"],
                key="co2_input"
            )

            # Optional notes
            notes = st.text_area("Notes (optional)", max_chars=200, key="notes_input")

            # Save button
            if st.button("💾 Save Test", use_container_width=True):
                # Validation
                errors = []
                for param, value in [
                    ("ph", ph), ("ammonia", ammonia), ("nitrite", nitrite),
                    ("nitrate", nitrate), ("kh", kh), ("temperature", temperature)
                ]:
                    if not isinstance(value, (int, float)):
                        errors.append(f"{param.upper()} must be numeric.")
                    elif not (0 <= value <= 1000):
                        errors.append(f"{param.upper()} value {value} is outside plausible range.")
                if errors:
                    st.error(" & ".join(errors))
                else:
                    # Timestamp
                    now_iso = datetime.datetime.utcnow().isoformat()
                    # Build data dict
                    data = {
                        "date": now_iso,
                        "ph": ph,
                        "ammonia": ammonia,
                        "nitrite": nitrite,
                        "nitrate": nitrate,
                        "kh": kh,
                        "co2_indicator": co2_indicator,
                        "temperature": temperature,
                        "notes": notes,
                    }
                    # Persist
                    save_water_test(data, tank_id)
                    st.success("✅ Test saved!")

                    # Check out-of-range
                    flagged = []
                    for param, value in [
                        ("ph", ph), ("ammonia", ammonia), ("nitrite", nitrite),
                        ("nitrate", nitrate), ("temperature", temperature)
                    ]:
                        if is_too_low(param, value) or is_too_high(param, value):
                            flagged.append(param)
                    if co2_indicator.startswith("Blue"):
                        flagged.append("co2 (low)")
                    elif co2_indicator.startswith("Yellow"):
                        flagged.append("co2 (high)")

                    if flagged:
                        st.error(
                            "⚠️ The most recent test has flagged parameters:\n" +
                            "\n".join(f"- {p.upper()}" for p in flagged)
                        )
                        for param in flagged:
                            show_parameter_advice(param, locals().get(param))

    # ─────────────────────────────────────────────────────────────────────
    # Desktop layout: inputs directly in sidebar
    # ─────────────────────────────────────────────────────────────────────
    else:
        date_in = st.sidebar.date_input("Date", value=date.today(), key="test_date")
        ph = st.sidebar.number_input(
            "pH", min_value=5.0, max_value=9.0, value=7.0,
            step=0.1, help=tooltips["ph"], key="ph_input"
        )
        temperature = st.sidebar.number_input(
            "Temp (℃)", min_value=15.0, max_value=35.0, value=26.0,
            step=0.5, help=tooltips["temperature"], key="temp_input"
        )
        ammonia = st.sidebar.number_input(
            "Ammonia (ppm)", min_value=0.0, max_value=8.0, value=0.0,
            step=0.1, help=tooltips["ammonia"], key="ammonia_input"
        )
        nitrite = st.sidebar.number_input(
            "Nitrite (ppm)", min_value=0.0, max_value=5.0, value=0.0,
            step=0.1, help=tooltips["nitrite"], key="nitrite_input"
        )
        nitrate = st.sidebar.number_input(
            "Nitrate (ppm)", min_value=0.0, max_value=80.0, value=5.0,
            step=1.0, help=tooltips["nitrate"], key="nitrate_input"
        )
        kh = st.sidebar.number_input(
            "KH (dKH)", min_value=0.0, max_value=20.0, value=2.0,
            step=0.1, help=tooltips["kh"], key="kh_input"
        )
        co2_indicator = st.sidebar.selectbox(
            "CO₂ Ind.", ["", "Blue (Low)", "Green (Ideal)", "Yellow (High)"],
            key="co2_input"
        )
        notes = st.sidebar.text_area("Notes (optional)", max_chars=200, key="notes_input")

        if st.sidebar.button("💾 Save Test"):
            errors = []
            for param, value in [
                ("ph", ph), ("ammonia", ammonia), ("nitrite", nitrite),
                ("nitrate", nitrate), ("kh", kh), ("temperature", temperature)
            ]:
                if not isinstance(value, (int, float)):
                    errors.append(f"{param.upper()} must be numeric.")
                elif not (0 <= value <= 1000):
                    errors.append(f"{param.upper()} value {value} is outside plausible range.")
            if errors:
                st.sidebar.error(" & ".join(errors))
            else:
                now_iso = datetime.datetime.utcnow().isoformat()
                data = {
                    "date": now_iso,
                    "ph": ph,
                    "ammonia": ammonia,
                    "nitrite": nitrite,
                    "nitrate": nitrate,
                    "kh": kh,
                    "co2_indicator": co2_indicator,
                    "temperature": temperature,
                    "notes": notes,
                }
                save_water_test(data, tank_id)
                st.sidebar.success("✅ Test saved!")

                flagged = []
                for param, value in [
                    ("ph", ph), ("ammonia", ammonia), ("nitrite", nitrite),
                    ("nitrate", nitrate), ("temperature", temperature)
                ]:
                    if is_too_low(param, value) or is_too_high(param, value):
                        flagged.append(param)
                if co2_indicator.startswith("Blue"):
                    flagged.append("co2 (low)")
                elif co2_indicator.startswith("Yellow"):
                    flagged.append("co2 (high)")

                if flagged:
                    st.sidebar.error(
                        "⚠️ The most recent test has flagged parameters:\n" +
                        "\n".join(f"- {p.upper()}" for p in flagged)
                    )
                    for param in flagged:
                        show_parameter_advice(param, locals().get(param))
