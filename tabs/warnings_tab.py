"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings, including pH compatibility for owned fish.
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
    st.header("⚠️ Test Warnings for Current Tank")

    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # --- Filter Controls (No change here) ---
    with st.expander("🔍 Filter Warnings"):
        col1, col2 = st.columns(2)
        with col1:
            date_range = st.date_input("Filter by date range", value=[], key=f"{key_prefix}warnings_date_range")
        with col2:
            filter_options = ["All"] + VALID_PARAMETERS
            params_to_filter = st.multiselect("Filter by parameter", options=filter_options, default=["All"], key=f"{key_prefix}warnings_param_filter")

    # --- Database Queries ---
    with get_connection() as conn:
        # 1. Get water tests
        query_tests = "..." # (Query is long, no change from previous version)
        # ... (logic to build and run the water test query is the same)
        
        # Build the query dynamically
        query_tests = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ?"
        )
        query_params: List[Any] = [tank_id]
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            query_tests += " AND date(wt.date) BETWEEN ? AND ?"
            query_params.extend([start_date.isoformat(), end_date.isoformat()])
        query_tests += " ORDER BY datetime(wt.date) DESC"
        filters_active = bool(date_range) or (bool(params_to_filter) and "All" not in params_to_filter)
        if not filters_active:
            query_tests += " LIMIT 10"
        tests_df = pd.read_sql(query_tests, conn, params=tuple(query_params))

        # 2. Get owned fish pH ranges for the current tank
        owned_fish_df = pd.read_sql_query("""
            SELECT f.species_name, f.phmin, f.phmax
            FROM owned_fish of
            JOIN fish f ON of.fish_id = f.fish_id
            WHERE of.tank_id = ? AND f.phmin IS NOT NULL AND f.phmax IS NOT NULL
        """, conn, params=(tank_id,))

    if tests_df.empty:
        st.info("No test data available for the selected tank or filters.")
        return

    # --- Warning Generation ---
    warnings: List[Dict[str, Any]] = []
    params_to_check = params_to_filter if params_to_filter and "All" not in params_to_filter else VALID_PARAMETERS

    for _, row in tests_df.iterrows():
        low_warnings, high_warnings, fish_ph_warnings = [], [], []

        # Check standard parameters
        for param in params_to_check:
            # ... (this part is the same as before) ...
            value = row.get(param)
            if value is None or pd.isna(value):
                continue
            low, high = SAFE_RANGES.get(param, (None, None))
            if low is not None and value < low:
                low_warnings.append({"param": param, "value": value})
            if high is not None and value > high:
                high_warnings.append({"param": param, "value": value})

        # NEW: Check pH for each owned fish
        current_ph = row.get("ph")
        if current_ph is not None and not owned_fish_df.empty:
            for _, fish in owned_fish_df.iterrows():
                if not (fish['phmin'] <= current_ph <= fish['phmax']):
                    msg = (
                        f"**{fish['species_name']}**: Current pH of **{current_ph:.2f}** "
                        f"is outside its preferred range of {fish['phmin']} - {fish['phmax']}."
                    )
                    fish_ph_warnings.append(msg)

        if low_warnings or high_warnings or fish_ph_warnings:
            warnings.append({
                "date": row["date"],
                "tank": row.get("tank_name", "Unknown"),
                "volume_l": row.get("volume_l"),
                "low_warnings": low_warnings,
                "high_warnings": high_warnings,
                "fish_ph_warnings": fish_ph_warnings # Add fish warnings to the dict
            })

    if not warnings:
        st.success("No out-of-range parameters found for the selected criteria.")
        return

    # --- Display Logic ---
    st.subheader("Results")
    for warning in warnings:
        failing_params = [item['param'].upper() for item in warning['low_warnings'] + warning['high_warnings']]
        if warning.get("fish_ph_warnings"):
            failing_params.append("FISH PH")
        title = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(sorted(list(set(failing_params))))}"

        with st.expander(title):
            # Display Fish pH Warnings First if they exist
            if warning.get("fish_ph_warnings"):
                with st.container(border=True):
                    st.subheader("🐠 Fish pH Incompatibility")
                    for fish_warning in warning["fish_ph_warnings"]:
                        st.warning(fish_warning)
            
            # Display standard parameter warnings
            col1, col2 = st.columns(2)
            # ... (rest of the display logic is the same) ...
            with col1:
                if warning['low_warnings'] or warning['high_warnings']:
                    st.subheader("Out of Range Parameters")
                    st.caption(f"Tank: {warning['tank']}")
                    st.markdown("---")
                    all_param_warnings = warning['low_warnings'] + warning['high_warnings']
                    for item in all_param_warnings:
                        param, value = item['param'], item['value']
                        safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                        st.metric(label=f"Parameter: {param.upper()}", value=f"{value:.2f}", delta=f"Safe Range: {safe_low} - {safe_high}", delta_color="inverse")
            with col2:
                if warning['low_warnings'] or warning['high_warnings']:
                    st.subheader("Recommended Actions")
                    # ... (dosing logic is the same) ...
                    volume_l = warning.get("volume_l")
                    if not volume_l or volume_l <= 0:
                        st.info("Set a tank volume in settings for dosing suggestions.")
                    for low_item in warning['low_warnings']:
                        param, value = low_item['param'], low_item['value']
                        plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0:
                            if param == 'kh':
                                dose = calculate_alkaline_buffer_dose(volume_l, max(0, 4.0 - value))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to raise KH.")
                            elif param == 'gh':
                                dose = calculate_equilibrium_dose(volume_l, max(0, 6.0 - value))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to raise GH.")
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