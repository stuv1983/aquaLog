# main.py (with Tools Tab)

"""
main.py – AquaLog Dashboard Launcher

Entry point for the Streamlit app. This script initializes the database,
sets the page configuration (title, icon), injects custom CSS, and dynamically
loads and renders the sidebar and all main application tabs,
orchestrating the user interface.
"""

from __future__ import annotations
import os
import sys
import streamlit as st
import base64
from typing import Callable

# ───────────────────────────────────────────────────────────
# Project root on path for utils & db
# ───────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(__file__)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ───────────────────────────────────────────────────────────
# Core utilities & DB
# ───────────────────────────────────────────────────────────
from utils import is_mobile
from aqualog_db import init_tables

# ───────────────────────────────────────────────────────────
# Sidebar entry
# ───────────────────────────────────────────────────────────
from sidebar.sidebar import sidebar_entry

# ───────────────────────────────────────────────────────────
# Import tab modules directly from the 'tabs' package
# ───────────────────────────────────────────────────────────
from tabs import (
    overview_tab,
    warnings_tab,
    data_analytics_tab,
    cycle_tab,
    plant_inventory_tab,
    fish_inventory_tab,
    equipment_tab,
    maintenance_tab,
    tools_tab,
    failed_tests_tab,  # Assuming this should be here too
)

def main() -> None:
    """
    Main entry point for the AquaLog Streamlit application.
    """
    init_tables()

    # --- FAVICON SETUP ---
    favicon = "🐠"
    try:
        with open("static/apple-touch-icon.png", "rb") as f:
            favicon_data = base64.b64encode(f.read()).decode()
            favicon = f"data:image/png;base64,{favicon_data}"
    except FileNotFoundError:
        pass  # Use default emoji if file not found

    st.set_page_config(
        page_title="AquaLog Dashboard",
        page_icon=favicon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for consistent UI elements
    st.markdown(
        """
        <style>
          div[data-baseweb="notification"][data-testid="stAlertContainer"] {
              border-radius:8px !important;
              border:1px solid #bbb !important;
              padding:0.75em !important;
              margin:0.5em 0 !important;
              font-weight:600 !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    sidebar_entry()

    try:
        tab_list = [
            "Overview", "Warnings", "Data & Analytics", "Cycle",
            "Plants", "Fish", "Equipment", "Maintenance", "Tools", "Failed Tests"
        ]
        tabs = st.tabs(tab_list)

        tab_map: dict[str, Callable] = {
            "Overview": overview_tab,
            "Warnings": warnings_tab,
            "Data & Analytics": data_analytics_tab,
            "Cycle": cycle_tab,
            "Plants": plant_inventory_tab,
            "Fish": fish_inventory_tab,
            "Equipment": equipment_tab,
            "Maintenance": maintenance_tab,
            "Tools": tools_tab,
            "Failed Tests": failed_tests_tab,
        }

        for i, title in enumerate(tab_list):
            with tabs[i]:
                # Call the corresponding function from our map
                tab_map[title]()

    except Exception as err:
        st.error(f"⚠️ An unexpected error occurred in a tab: {err}")
        st.exception(err) # Show full traceback for debugging

if __name__ == "__main__":
    main()