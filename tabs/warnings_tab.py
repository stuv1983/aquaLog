"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings, including pH and temperature compatibility for owned fish.
"""
from __future__ import annotations
from typing import Any, List, Dict
from datetime import date

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature", "co2_indicator"]

def warnings_tab(key_prefix=""):
    st.header("⚠️ Test Warnings for Current Tank")

    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # --- Filter Controls ---
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
        query_tests = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh, wt.co2_indicator "
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

        # 2. Get owned fish parameter ranges for the current tank
        owned_fish_df = pd.read_sql_query("""
            SELECT f.species_name, f.phmin, f.phmax, f.temperature_min, f.temperature_max
            FROM owned_fish of
            JOIN fish f ON of.fish_id = f.fish_id
            WHERE of.tank_id = ?
        """, conn, params=(tank_id,))

    if tests_df.empty:
        st.info("No test data available for the selected tank or filters.")
        return

    # --- Warning Generation ---
    warnings: List[Dict[str, Any]] = []
    params_to_check = params_to_filter if params_to_filter and "All" not in params_to_filter else VALID_PARAMETERS

    for _, row in tests_df.iterrows():
        low_warnings, high_warnings, fish_compatibility_warnings = [], [], []

        # Check standard parameters
        for param in params_to_check:
            value = row.get(param)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            if param == "co2_indicator":
                if "Blue" in value: low_warnings.append({"param": param, "value": value})
                elif "Yellow" in value: high_warnings.append({"param": param, "value": value})
            elif pd.notna(value):
                low, high = SAFE_RANGES.get(param, (None, None))
                if low is not None and float(value) < low: low_warnings.append({"param": param, "value": float(value)})
                if high is not None and float(value) > high: high_warnings.append({"param": param, "value": float(value)})

        # NEW: Check pH and Temperature for each owned fish
        current_ph = row.get("ph")
        current_temp = row.get("temperature")
        if not owned_fish_df.empty:
            for _, fish in owned_fish_df.iterrows():
                # pH Check
                if pd.notna(current_ph) and pd.notna(fish['phmin']) and not (fish['phmin'] <= current_ph <= fish['phmax']):
                    msg = f"**{fish['species_name']}**: Current pH of **{current_ph:.1f}** is outside its preferred range of {fish['phmin']:.1f} - {fish['phmax']:.1f}."
                    fish_compatibility_warnings.append(msg)
                # Temperature Check
                if pd.notna(current_temp) and pd.notna(fish['temperature_min']) and not (fish['temperature_min'] <= current_temp <= fish['temperature_max']):
                    msg = f"**{fish['species_name']}**: Temp **{current_temp:.1f}°C** is outside its preferred range of {fish['temperature_min']:.1f}°C - {fish['temperature_max']:.1f}°C."
                    fish_compatibility_warnings.append(msg)

        if low_warnings or high_warnings or fish_compatibility_warnings:
            warnings.append({
                "date": row["date"], "tank": row.get("tank_name", "Unknown"), "volume_l": row.get("volume_l"),
                "low_warnings": low_warnings, "high_warnings": high_warnings,
                "fish_compatibility_warnings": fish_compatibility_warnings
            })

    if not warnings:
        st.success("No out-of-range parameters found for the selected criteria.")
        return

    # --- Display Logic ---
    st.subheader("Results")
    for warning in warnings:
        failing_params = [item['param'].upper() for item in warning['low_warnings'] + warning['high_warnings']]
        if warning.get("fish_compatibility_warnings"):
            failing_params.append("FISH COMPATIBILITY")
        title = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(sorted(list(set(failing_params))))}"

        with st.expander(title):
            # Display Fish Compatibility Warnings First
            if warning.get("fish_compatibility_warnings"):
                with st.container(border=True):
                    st.subheader("🐠 Fish Compatibility Warnings")
                    for fish_warning in warning["fish_compatibility_warnings"]:
                        st.warning(fish_warning)
            
            # Display standard parameter warnings
            if warning['low_warnings'] or warning['high_warnings']:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Out of Range Parameters")
                    st.caption(f"Tank: {warning['tank']}")
                    st.markdown("---")
                    for item in warning['low_warnings'] + warning['high_warnings']:
                        param, value = item['param'], item['value']
                        if param == 'co2_indicator':
                            st.metric(label=f"Parameter: {param.upper()}", value=str(value), delta="Should be Green", delta_color="off")
                        else:
                            safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                            st.metric(label=f"Parameter: {param.upper()}", value=f"{value:.2f}", delta=f"Safe Range: {safe_low}–{safe_high}", delta_color="inverse")
                with col2:
                    st.subheader("Recommended Actions")
                    volume_l = warning.get("volume_l")
                    if not volume_l or volume_l <= 0:
                        st.info("Set tank volume in settings for dosing suggestions.")
                    for low_item in warning['low_warnings']:
                        param, value = low_item['param'], low_item['value']
                        plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param not in ['co2_indicator']:
                            if param == 'kh': dose = calculate_alkaline_buffer_dose(volume_l, max(0, 4.0 - value)); plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to raise KH.")
                            elif param == 'gh': dose = calculate_equilibrium_dose(volume_l, max(0, 6.0 - value)); plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to raise GH.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---")
                    for high_item in warning['high_warnings']:
                        param, value = high_item['param'], high_item['value']
                        plan_list = ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param in ['ammonia', 'nitrite']:
                            dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system=True)
                            plan_list.insert(1, f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose_ml:.0f}ml / {dose_oz:.1f}oz** of FritzZyme 7.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---")