"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings, including for CO2 indicator status,
and provides dosing calculations or a prompt to set the volume.
"""
from __future__ import annotations
from typing import Any, List, Dict
from datetime import date

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose

# FIX: Added 'co2_indicator' to the list of parameters to validate
VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature", "co2_indicator"]

def warnings_tab(key_prefix=""):
    """
    Renders the warnings tab for the currently selected tank with optional filters.
    """
    st.header("⚠️ Test Warnings for Current Tank")

    tank_id = st.session_state.get("tank_id")

    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # --- Filter Controls ---
    with st.expander("🔍 Filter Warnings"):
        col1, col2 = st.columns(2)
        with col1:
            date_range = st.date_input(
                "Filter by date range",
                value=[],
                key=f"{key_prefix}warnings_date_range"
            )
        with col2:
            filter_options = ["All"] + VALID_PARAMETERS
            params_to_filter = st.multiselect(
                "Filter by parameter",
                options=filter_options,
                default=["All"],
                key=f"{key_prefix}warnings_param_filter"
            )

    # --- Dynamic Query Building ---
    with get_connection() as conn:
        query = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh, wt.co2_indicator " # Ensure co2_indicator is selected
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ?"
        )
        query_params: List[Any] = [tank_id]

        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            query += " AND date(wt.date) BETWEEN ? AND ?"
            query_params.extend([start_date.isoformat(), end_date.isoformat()])

        query += " ORDER BY datetime(wt.date) DESC"

        filters_active = bool(date_range) or (bool(params_to_filter) and "All" not in params_to_filter)
        if not filters_active:
            query += " LIMIT 10"

        tests_df = pd.read_sql(query, conn, params=tuple(query_params))

    if tests_df.empty:
        st.info("No test data available for the selected tank or filters.")
        return

    # --- Warning Generation ---
    warnings: List[Dict[str, Any]] = []
    if not params_to_filter or "All" in params_to_filter:
        params_to_check = VALID_PARAMETERS
    else:
        params_to_check = [p for p in params_to_filter if p in VALID_PARAMETERS]

    for _, row in tests_df.iterrows():
        low_warnings, high_warnings, fish_ph_warnings = [], [], []

        for param in params_to_check:
            value = row.get(param)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            # FIX: Add special handling for the categorical 'co2_indicator'
            if param == "co2_indicator":
                if "Blue" in value:
                    low_warnings.append({"param": param, "value": value})
                elif "Yellow" in value:
                    high_warnings.append({"param": param, "value": value})
            # Original logic for numeric parameters
            elif pd.notna(value):
                low, high = SAFE_RANGES.get(param, (None, None))
                if low is not None and float(value) < low:
                    low_warnings.append({"param": param, "value": float(value)})
                if high is not None and float(value) > high:
                    high_warnings.append({"param": param, "value": float(value)})

        if low_warnings or high_warnings:
            warnings.append({
                "date": row["date"],
                "tank": row.get("tank_name", "Unknown"),
                "volume_l": row.get("volume_l"),
                "low_warnings": low_warnings,
                "high_warnings": high_warnings,
            })

    if not warnings:
        st.success("No out-of-range parameters found for the selected criteria.")
        return

    # --- Display Logic ---
    st.subheader("Results")
    for warning in warnings:
        all_warnings = warning['low_warnings'] + warning['high_warnings']
        failing_params = [item['param'].upper() for item in all_warnings]
        title = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(sorted(list(set(failing_params))))}"

        with st.expander(title):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Out of Range Details")
                st.caption(f"Tank: {warning['tank']}")
                st.markdown("---")
                for item in all_warnings:
                    param, value = item['param'], item['value']
                    # FIX: Custom display for co2_indicator metric
                    if param == 'co2_indicator':
                        st.metric(label=f"Parameter: {param.upper()}", value=str(value), delta="Should be Green", delta_color="off")
                    else:
                        safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                        st.metric(label=f"Parameter: {param.upper()}", value=f"{value:.2f}", delta=f"Safe Range: {safe_low}–{safe_high}", delta_color="inverse")

            with col2:
                st.subheader("Recommended Actions")
                volume_l = warning.get("volume_l")
                if not volume_l or volume_l <= 0:
                    st.info("Set tank volume in sidebar settings for dosing suggestions.")

                for low_item in warning['low_warnings']:
                    param, value = low_item['param'], low_item['value']
                    plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                    if volume_l and volume_l > 0 and param not in ['co2_indicator']:
                        if param == 'kh':
                            dose = calculate_alkaline_buffer_dose(volume_l, max(0, 4.0 - value))
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer.")
                        elif param == 'gh':
                            dose = calculate_equilibrium_dose(volume_l, max(0, 6.0 - value))
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium.")
                    for step in plan_list:
                        st.markdown(f" • {step}")
                    st.markdown("---")

                for high_item in warning['high_warnings']:
                    param, value = high_item['param'], high_item['value']
                    plan_list = ACTION_PLANS.get(param, []).copy()
                    if volume_l and volume_l > 0 and param in ['ammonia', 'nitrite']:
                        dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system=True)
                        plan_list = [item for item in plan_list if "Dose with FritzZyme 7" not in item]
                        plan_list.insert(1, f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose_ml:.0f}ml / {dose_oz:.1f}oz** of FritzZyme 7.")
                    for step in plan_list:
                        st.markdown(f" • {step}")
                    st.markdown("---")