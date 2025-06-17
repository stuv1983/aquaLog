# main.py (Reverted)

"""
main.py – AquaLog Dashboard Launcher

Entry point for the Streamlit app:
- Sets up page config and favicons
- Injects custom CSS for toasts & mobile tweaks
- Initializes/migrates database schema (persisted on-disk)
- Renders the sidebar and main tabs
- Catches and displays unexpected errors
"""

import os
import sys
import streamlit as st

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
# Sidebar entry (refactored into its own package)
# ───────────────────────────────────────────────────────────
from sidebar.sidebar import sidebar_entry

# ───────────────────────────────────────────────────────────
# Load tab modules dynamically
# ───────────────────────────────────────────────────────────
import importlib.machinery
import importlib.util

def load_tab(func_name: str, rel_path: str):
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
failed_tests_tab       = load_tab("failed_tests_tab",    "tabs/failed_tests_tab.py")
plant_inventory_tab    = load_tab("plant_inventory_tab", "tabs/plant_inventory_tab.py")
fish_inventory_tab     = load_tab("fish_inventory_tab",  "tabs/fish_inventory_tab.py")
equipment_tab          = load_tab("equipment_tab",       "tabs/equipment_tab.py")
maintenance_tab        = load_tab("maintenance_tab",     "tabs/maintenance_tab.py")

VERSION = "v3.7.1"
RELEASE_NOTES = """
### v3.7.1 (2025-06-12)
* **Fix:** Database now persists to `aqualog.db` on disk.
* **Fix:** `init_tables()` called at startup to initialize/migrate schema.
"""

def main() -> None:
    # Initialize DB
    init_tables()

    # Page config
    st.set_page_config(
        page_title="AquaLog Dashboard",
        page_icon="favicon-32x32.png",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.write(
        """
        <link rel="manifest" href="site.webmanifest">
        <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
        <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
        """,
        unsafe_allow_html=True,
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
        tabs = st.tabs([
            "Overview", "Warnings", "Data & Analytics", "Cycle",
            "Failed Tests", "Plants", "Fish", "Equipment", "Maintenance",
        ])
        tab_map = {
            "Overview": overview_tab,
            "Warnings": warnings_tab,
            "Data & Analytics": data_analytics_tab,
            "Cycle": cycle_tab,
            "Failed Tests": failed_tests_tab,
            "Plants": plant_inventory_tab,
            "Fish": fish_inventory_tab,
            "Equipment": equipment_tab,
            "Maintenance": maintenance_tab,
        }
        for idx, title in enumerate(tab_map):
            with tabs[idx]:
                tab_map[title]()
    except Exception as err:
        st.error(f"⚠️ An unexpected error occurred in a tab: {err}")

if __name__ == "__main__":
    main()