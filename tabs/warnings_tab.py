"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the last 10 tests, including Seachem dosing
advice for low KH and GH based on tank volume.
"""
from __future__ import annotations
from typing import Any, List, Dict

import pandas as pd
import streamlit as st

# Modern DB imports
from aqualog_db.connection import get_connection

from config import SAFE_RANGES, ACTION_PLANS

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"]


def warnings_tab() -> None:
    st.header("⚠️ Last 10 Test Warnings")

    # Use context manager to get a valid DB connection
    with get_connection() as conn:
        tanks_df = pd.read_sql("SELECT id, name FROM tanks", conn)
        # Query last 10 tests with tank names
        query = (
            "SELECT wt.date, t.name AS tank_name, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "ORDER BY datetime(wt.date) DESC "
            "LIMIT 10"
        )
        tests_df = pd.read_sql(query, conn)

    # Ensure tanks exist
    if tanks_df.empty:
        st.warning("No tanks found. Add a tank in Settings first.")
        return

    # Ensure tests exist
    if tests_df.empty:
        st.info("No test data available.")
        return

    # Build warnings list
    warnings: List[Dict[str, Any]] = []
    for _, row in tests_df.iterrows():
        test_warnings: List[str] = []
        for param in VALID_PARAMETERS:
            value = row.get(param)
            if value is None or pd.isna(value):  # Skip missing
                continue
            low, high = SAFE_RANGES.get(param, (None, None))
            if low is not None and value < low:
                test_warnings.append(param)
            elif high is not None and value > high:
                test_warnings.append(param)
        if test_warnings:
            warnings.append({
                "date": row["date"],
                "tank": row.get("tank_name", "Unknown"),
                "warnings": test_warnings,
            })

    # Display collapsible warnings
    for w in warnings:
        with st.expander(f"Test from {w['date']} – {w['tank']} ({', '.join(w['warnings'])})"):
            for param in w['warnings']:
                plan = ACTION_PLANS.get(param)
                if plan:
                    st.markdown(f"- **{param.title()}**: {plan}")
