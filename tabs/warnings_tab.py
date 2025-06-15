"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the last 10 tests for the currently selected tank.
"""
from __future__ import annotations
from typing import Any, List, Dict

import pandas as pd
import streamlit as st

# Modern DB imports
from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"]


def warnings_tab(key_prefix=""):
    """
    Renders the warnings tab for the currently selected tank.
    Args:
        key_prefix (str): A string to prefix all widget keys to ensure uniqueness.
    """
    st.header("⚠️ Test Warnings for Current Tank")

    # FIX: Get the current tank_id from the session state
    tank_id = st.session_state.get("tank_id")

    # FIX: Handle the case where no tank is selected
    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # Use context manager to get a valid DB connection
    with get_connection() as conn:
        # FIX: Modify the query to filter by the selected tank_id and get the last 10 tests for that tank
        query = (
            "SELECT wt.date, t.name AS tank_name, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ? "
            "ORDER BY datetime(wt.date) DESC "
            "LIMIT 10"
        )
        # FIX: Pass the tank_id as a parameter to the query to prevent SQL injection
        tests_df = pd.read_sql(query, conn, params=(tank_id,))

    # Ensure tests exist for the selected tank
    if tests_df.empty:
        st.info("No test data available for the selected tank.")
        return

    # Build warnings list
    warnings: List[Dict[str, Any]] = []
    for _, row in tests_df.iterrows():
        low_warnings: List[str] = []
        high_warnings: List[str] = []

        for param in VALID_PARAMETERS:
            value = row.get(param)
            if value is None or pd.isna(value):  # Skip missing
                continue
            
            low, high = SAFE_RANGES.get(param, (None, None))
            
            if low is not None and value < low:
                low_warnings.append(param)
            
            if high is not None and value > high:
                high_warnings.append(param)

        if low_warnings or high_warnings:
            warnings.append({
                "date": row["date"],
                "tank": row.get("tank_name", "Unknown"),
                "low_warnings": low_warnings,
                "high_warnings": high_warnings,
            })

    # Display collapsible warnings
    if not warnings:
        st.success("No warnings found in the last 10 tests for this tank.")
        return

    for idx, w in enumerate(warnings):
        all_warnings = w['low_warnings'] + w['high_warnings']
        expander_title = f"Test from {w['date']} – {w['tank']} ({', '.join(all_warnings)})"
        
        with st.expander(expander_title):
            for param in w['low_warnings']:
                plan_list = LOW_ACTION_PLANS.get(param)
                if plan_list:
                    for item in plan_list:
                        st.markdown(f"- {item}")
            
            for param in w['high_warnings']:
                plan_list = ACTION_PLANS.get(param)
                if plan_list:
                    for item in plan_list:
                        st.markdown(f"- {item}")