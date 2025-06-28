# main.py (with Tools Tab)

"""
main.py – AquaLog Dashboard Launcher

Entry point for the Streamlit app. This script initializes the database,
sets the page configuration (title, icon), injects custom CSS, and dynamically
loads and renders the sidebar and all main application tabs,
orchestrating the user interface.
"""

from __future__ import annotations # Added for type hinting consistency

import os
import sys
import streamlit as st
import base64
from typing import Callable # Ensure Callable is imported for type hints

# ───────────────────────────────────────────────────────────
# Project root on path for utils & db
# ───────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(__file__)
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
# Load tab modules dynamically
# ───────────────────────────────────────────────────────────
import importlib.machinery
import importlib.util

def load_tab(func_name: str, rel_path: str) -> Callable: # Added return type hint
    """
    Dynamically loads a function from a specified module path,
    allowing for flexible and modular tab management.

    Args:
        func_name (str): The name of the function to load from the module.
        rel_path (str): The relative path to the module file (e.g., "tabs/overview_tab.py").

    Returns:
        Callable: The loaded function object.
    """
    spec = importlib.util.spec_from_file_location(
        func_name,
        os.path.join(ROOT_DIR, rel_path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)

# Correctly load each tab function by its defined name
overview_tab           = load_tab("overview_tab",        "tabs/overview_tab.py")
warnings_tab           = load_tab("warnings_tab",        "tabs/warnings_tab.py")
data_analytics_tab     = load_tab("data_analytics_tab",  "tabs/data_analytics_tab.py")
cycle_tab              = load_tab("cycle_tab",           "tabs/cycle_tab.py")
plant_inventory_tab    = load_tab("plant_inventory_tab", "tabs/plant_inventory_tab.py")
fish_inventory_tab     = load_tab("fish_inventory_tab",  "tabs/fish_inventory_tab.py")
equipment_tab          = load_tab("equipment_tab",       "tabs/equipment_tab.py")
maintenance_tab        = load_tab("maintenance_tab",     "tabs/maintenance_tab.py")
# --- IMPORT THE NEW TOOLS TAB ---
tools_tab              = load_tab("tools_tab", "tabs/tools_tab.py")

# The VERSION and RELEASE_NOTES are now defined only in config.py
# and are displayed via sidebar/release_notes.py

def main() -> None:
    """
    Main entry point for the AquaLog Streamlit application.

    This function performs the following setup and rendering tasks:
    1. Initializes the SQLite database and ensures tables are created.
    2. Configures the Streamlit page, including title, favicon, and layout.
    3. Injects custom CSS for a consistent UI theme.
    4. Renders the main sidebar components, including tank selection and input forms.
    5. Dynamically loads and displays the main application tabs (Overview, Warnings,
       Data & Analytics, Cycle, Plants, Fish, Equipment, Maintenance, and Tools),
       allowing users to navigate through different features.
    """
    # Initialize DB
    init_tables()

    # --- FAVICON SETUP ---
    favicon = None
    try:
        with open("static/apple-touch-icon.png", "rb") as f:
            favicon_data = base64.b64encode(f.read()).decode()
        favicon = f"data:image/png;base64,{favicon_data}"
    except FileNotFoundError:
        favicon = "🐠"

    # Page config
    st.set_page_config(
        page_title="AquaLog Dashboard",
        page_icon=favicon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS
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

    # Sidebar + Main Tabs
    sidebar_entry()

    try:
        # --- ADD "Tools" TO THE UI ---
        tabs = st.tabs([
            "Overview", "Warnings", "Data & Analytics", "Cycle",
            "Plants", "Fish", "Equipment", "Maintenance", "Tools"
        ])
        tab_map = {
            "Overview": overview_tab,
            "Warnings": warnings_tab,
            "Data & Analytics": data_analytics_tab,
            "Cycle": cycle_tab,
            "Plants": plant_inventory_tab,
            "Fish": fish_inventory_tab,
            "Equipment": equipment_tab,
            "Maintenance": maintenance_tab,
            "Tools": tools_tab,
        }
        for idx, title in enumerate(tab_map):
            with tabs[idx]:
                tab_map[title]()
    except Exception as err:
        st.error(f"⚠️ An unexpected error occurred in a tab: {err}")

if __name__ == "__main__":
    main()