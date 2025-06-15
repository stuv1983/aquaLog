"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the last 10 tests for the currently selected tank,
including calculated dosages for all relevant parameters based on tank volume.
"""
from __future__ import annotations
from typing import Any, List, Dict

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils.chemistry import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"]

def warnings_tab(key_prefix=""):
    """
    Renders the warnings tab for the currently selected tank.
    Args:
        key_prefix (str): A string to prefix all widget keys to ensure uniqueness.
    """
    st.header("⚠️ Test Warnings for Current Tank")

    tank_id = st.session_state.get("tank_id")

    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    with get_connection() as conn:
        query = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ? "
            "ORDER BY datetime(wt.date) DESC "
            "LIMIT 10"
        )
        tests_df = pd.read_sql(query, conn, params=(tank_id,))

    if tests_df.empty:
        st.info("No test data available for the selected tank.")
        return

    warnings: List[Dict[str, Any]] = []
    for _, row in tests_df.iterrows():
        low_warnings: List[Dict[str, Any]] = []
        high_warnings: List[Dict[str, Any]] = []

        for param in VALID_PARAMETERS:
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
        st.success("No out-of-range parameters found in the last 10 tests for this tank.")
        return

    # --- NEW, CLEANER DISPLAY LOGIC ---
    for warning in warnings:
        with st.container(border=True):
            col1, col2 = st.columns(2)

            # --- Left Column: The Problem ---
            with col1:
                st.subheader(f"Test: {warning['date'][:10]}")
                st.caption(f"Tank: {warning['tank']}")
                st.markdown("---")

                all_warnings = warning['low_warnings'] + warning['high_warnings']
                for item in all_warnings:
                    param = item['param']
                    value = item['value']
                    safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                    
                    st.metric(
                        label=f"Out of Range: {param.upper()}",
                        value=f"{value:.2f}",
                        delta=f"Safe: {safe_low} - {safe_high}",
                        delta_color="inverse"
                    )

            # --- Right Column: The Solution ---
            with col2:
                st.subheader("Recommended Actions")
                
                volume_l = warning.get("volume_l")
                
                # Process low warnings
                for low_item in warning['low_warnings']:
                    param, value = low_item['param'], low_item['value']
                    plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                    
                    if volume_l and volume_l > 0:
                        if param == 'kh':
                            dose = calculate_alkaline_buffer_dose(volume_l, max(0, 6.0 - value))
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer.")
                        elif param == 'gh':
                            dose = calculate_equilibrium_dose(volume_l, max(0, 6.0 - value))
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium.")
                    
                    for step in plan_list:
                        st.markdown(f" • {step}")

                # Process high warnings
                for high_item in warning['high_warnings']:
                    param, value = high_item['param'], high_item['value']
                    plan_list = ACTION_PLANS.get(param, []).copy()
                    
                    if volume_l and volume_l > 0 and param in ['ammonia', 'nitrite']:
                        dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system=True)
                        plan_list = [item for item in plan_list if "Dose with FritzZyme 7" not in item]
                        plan_list.insert(1, f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose_ml:.0f}ml / {dose_oz:.1f}oz** of FritzZyme 7.")

                    for step in plan_list:
                        st.markdown(f" • {step}")
        
        st.markdown("<br>", unsafe_allow_html=True) # Add vertical space between cards
