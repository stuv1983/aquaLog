# sidebar/sidebar.py

"""
sidebar.py – Main Sidebar UI Assembler

This module's `sidebar_entry` function is the main entry point for rendering the
entire Streamlit sidebar. It calls other modules to render the tank selector,
water test input form, application settings panel, and release notes,
organizing them into a cohesive sidebar interface.
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
    It orchestrates the rendering of all sidebar components.

    It fetches tank data, populates the tank selector, and then renders
    the water test form, a collapsible settings panel, and release notes.
    """
    # Fetch all tanks from the database to populate the tank selector
    tanks = TankRepository().fetch_all()
    
    # Create a map of tank IDs to their names and volumes for easy access
    tank_map: Dict[int, Dict[str, Any]] = {
        t["id"]: {"name": t["name"], "volume": t.get("volume_l", 0.0)}
        for t in tanks
    }

    # Render the tank selection dropdown at the top of the sidebar
    render_tank_selector(tank_map)
    
    # Render the water test input form
    render_water_test_form(tank_map)
    
    # Render the settings panel within a collapsible expander
    with st.sidebar.expander("⚙️ Settings", expanded=False, icon="💧"):
        render_settings_panel(tank_map)
        
    # Render the release notes section
    render_release_notes()