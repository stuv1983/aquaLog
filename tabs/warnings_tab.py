"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the last 10 tests for the currently selected tank,
including calculated dosages for low KH and GH based on tank volume.
"""
from __future__ import annotations
from typing import Any, List, Dict

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils.chemistry import calculate_alkaline_buffer_dose, calculate_equilibrium_dose

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
        # FIX: Fetch tank volume (volume_l) to use in dosage calculations.
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
        # FIX: Store both the parameter name and its value for calculations.
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
        st.success("No warnings found in the last 10 tests for this tank.")
        return

    for idx, w in enumerate(warnings):
        all_warning_params = [item['param'] for item in w['low_warnings']] + [item['param'] for item in w['high_warnings']]
        expander_title = f"Test from {w['date']} – {w['tank']} ({', '.join(all_warning_params)})"
        
        with st.expander(expander_title):
            # --- Low Parameter Warnings & Dosing ---
            for warning_info in w['low_warnings']:
                param = warning_info["param"]
                value = warning_info["value"]
                plan_list = LOW_ACTION_PLANS.get(param, []).copy() # Use .copy() to avoid modifying the original
                
                # FIX: Calculate and add dosage advice if tank volume is known
                volume_l = w.get("volume_l")
                if volume_l and volume_l > 0:
                    if param == 'kh':
                        target_kh = 6.0  # Sensible default target
                        delta_kh = max(0, target_kh - value)
                        if delta_kh > 0:
                            dose = calculate_alkaline_buffer_dose(volume_l, delta_kh)
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to reach ~{target_kh} dKH.")
                    elif param == 'gh':
                        target_gh = 6.0  # Sensible default target
                        delta_gh = max(0, target_gh - value)
                        if delta_gh > 0:
                            dose = calculate_equilibrium_dose(volume_l, delta_gh)
                            plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to reach ~{target_gh} dGH.")
                
                for item in plan_list:
                    st.markdown(f"- {item}")
            
            # --- High Parameter Warnings ---
            for warning_info in w['high_warnings']:
                param = warning_info["param"]
                plan_list = ACTION_PLANS.get(param, [])
                for item in plan_list:
                    st.markdown(f"- {item}")