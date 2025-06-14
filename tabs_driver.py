"""
tabs_driver.py – Main Tabs Driver (v3.3.1)
Renders the sidebar and all primary application tabs in the correct order.
Updated: 2025-06-15
"""
from __future__ import annotations

import streamlit as st

# ── individual tab modules ──────────────────────────────────────────────────────
from tabs.sidebar_entry        import sidebar_entry
from tabs.overview_tab         import overview_tab
from tabs.warnings_tab         import warnings_tab
from tabs.data_analytics_tab   import data_analytics_tab
from tabs.cycle_tab            import cycle_tab
from tabs.failed_tests_tab     import failed_tests_tab
from tabs.plant_inventory_tab  import plant_inventory_tab
from tabs.fish_inventory_tab   import fish_inventory_tab
from tabs.equipment_tab        import equipment_tab
from tabs.maintenance_tab      import maintenance_tab
# ────────────────────────────────────────────────────────────────────────────────

# (label, render-function) pairs - keeping them side-by-side prevents drift
TAB_DEFS = (
    ("Overview",       overview_tab),
    ("Warnings",       warnings_tab),
    ("Data Analytics", data_analytics_tab),
    ("Cycle",          cycle_tab),
    ("Failed Tests",   failed_tests_tab),
    ("Plants",         plant_inventory_tab),
    ("Fish",           fish_inventory_tab),
    ("Equipment",      equipment_tab),
    ("Maintenance",    maintenance_tab),
)


def render_tabs() -> None:
    """Kick off sidebar and main-area tabs."""
    st.set_page_config(page_title="AquaLog", layout="wide")
    sidebar_entry()

    labels, funcs = zip(*TAB_DEFS)           # 1-to-1 label/function mapping
    tab_objs = st.tabs(labels)

    for tab, fn in zip(tab_objs, funcs):
        with tab:
            fn()


if __name__ == "__main__":
    render_tabs()
