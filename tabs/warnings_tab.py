"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the currently selected tank. Each warning is
now within a collapsible expander to keep the UI clean.
"""
from __future__ import annotations
from typing import Any, List, Dict
from datetime import date

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"]

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
            "wt.ph, wt.temperature, wt.kh, wt.gh "
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
        low_warnings, high_warnings = [], []
        for param in params_to_check:
            value = row.get(param)
            if value is None or pd.isna(value):
                continue
            low, high = SAFE_RANGES.get(param, (None, None))
            if low is not None and value < low:
                low_warnings.append({"param": param, "value": value})
            if high is not None and value > high:
                high_warnings.append({"param": param, "value": value})
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
        # Create a summary of failing parameters for the expander title
        failing_low = [item['param'].upper() for item in warning['low_warnings']]
        failing_high = [item['param'].upper() for item in warning['high_warnings']]
        title = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(failing_low + failing_high)}"

        # Use an st.expander to make the details collapsible
        with st.expander(title):
            col1, col2 = st.columns(2)

            # Left Column: The Problem
            with col1:
                st.subheader("Out of Range Details")
                st.caption(f"Tank: {warning['tank']}")
                st.markdown("---")

                all_warnings = warning['low_warnings'] + warning['high_warnings']
                for item in all_warnings:
                    param, value = item['param'], item['value']
                    safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                    st.metric(
                        label=f"Parameter: {param.upper()}",
                        value=f"{value:.2f}",
                        delta=f"Safe Range: {safe_low} - {safe_high}",
                        delta_color="inverse"
                    )

            # Right Column: The Solution
            with col2:
                st.subheader("Recommended Actions")
                volume_l = warning.get("volume_l")

                if not volume_l or volume_l <= 0:
                    st.info("Set a tank volume in the sidebar settings to receive automatic dosing suggestions.")

                # Low Parameter Warnings
                for low_item in warning['low_warnings']:
                    param, value = low_item['param'], low_item['value']
                    plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                    if volume_l and volume_l > 0:
                        if param == 'kh':
                            dose = calculate_alkaline_buffer_dose(volume_l, max(0, 4.0 - value)) # Target a minimum of 4.0
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to raise KH.")
                        elif param == 'gh':
                            dose = calculate_equilibrium_dose(volume_l, max(0, 6.0 - value)) # Target a minimum of 6.0
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to raise GH.")
                    for step in plan_list:
                        st.markdown(f" • {step}")
                    st.markdown("---")


                # High Parameter Warnings
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
