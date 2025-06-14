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
from aqualog_db.legacy import fetch_all_tanks, fetch_recent_tests

from config import SAFE_RANGES, ACTION_PLANS

VALID_PARAMETERS = ["ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"]


def warnings_tab() -> None:
    st.header("⚠️ Last 10 Test Warnings")

    # Fetch data
    tanks = fetch_all_tanks()
    if not tanks:
        st.warning("No tanks found. Add a tank in Settings first.")
        return

    # For simplicity show warnings across all tanks
    tests = fetch_recent_tests(limit=10)
    if tests.empty:
        st.info("No test data available.")
        return

    # Build warnings list
    warnings: List[Dict[str, Any]] = []
    for _, row in tests.iterrows():
        test_warnings: List[str] = []
        for param in VALID_PARAMETERS:
            value = row.get(param)
            if value is None or pd.isna(value):
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
        with st.expander(f"Test from {w['date']} ({', '.join(w['warnings'])})"):
            tank = w['tank']
            st.write(f"**Tank:** {tank}")
            for param in w['warnings']:
                plan = ACTION_PLANS.get(param)
                if plan:
                    st.markdown(f"- **{param.title()}**: {plan}")
