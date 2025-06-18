# sidebar/sidebar.py

"""
sidebar.py – Main Sidebar UI Assembler

This module's `sidebar_entry` function is the main entry point for rendering the
entire sidebar. It calls other modules to render the tank selector, water test
form, settings panel, and release notes.
"""

import streamlit as st
from typing import Dict, Any

from aqualog_db.repositories import TankRepository
from .tank_selector import render_tank_selector
from .water_test_form import render_water_test_form
from .settings_panel import render_settings_panel
from .release_notes import render_release_notes

def sidebar_entry() -> None:
    """
    This is the main entry point function for the sidebar.
    It organizes all sidebar components.
    """
    tanks = TankRepository().fetch_all()
    tank_map: Dict[int, Dict[str, Any]] = {
        t["id"]: {"name": t["name"], "volume": t.get("volume_l", 0.0)}
        for t in tanks
    }

    render_tank_selector(tank_map)
    render_water_test_form(tank_map)
    
    with st.sidebar.expander("⚙️ Settings", expanded=False, icon="💧"):
        render_settings_panel(tank_map)
        
    render_release_notes()