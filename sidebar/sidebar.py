# sidebar/sidebar.py

"""
sidebar.py – Main Sidebar UI Assembler

This module's `sidebar_entry` function is the main entry point for rendering the
entire Streamlit sidebar. It calls other modules to render the tank selector,
water test input form, application settings panel, and release notes,
organizing them into a cohesive sidebar interface.
"""

from __future__ import annotations # Added for type hinting consistency

import streamlit as st
from typing import Dict, Any # Keep Dict and Any for other uses if necessary

from aqualog_db.repositories import TankRepository
from aqualog_db.repositories.tank import TankRecord # Import TankRecord TypedDict
from .tank_selector import render_tank_selector
from .water_test_form import render_water_test_form
from .settings_panel import render_settings_panel
from .release_notes import render_release_notes

def sidebar_entry() -> None:
    """
    This is the main entry point function for the Streamlit sidebar.
    It orchestrates the rendering of all primary sidebar components, providing
    navigation and core functionalities to the user.

    The orchestration involves:
    1.  Fetching all tank data from the database to establish context.
    2.  Populating and rendering the **Tank Selector** dropdown, allowing users
        to switch between their aquariums.
    3.  Rendering the **Water Test Input Form** for logging new water quality readings.
    4.  Displaying a collapsible **Settings Panel** where users can manage tanks,
        customize ranges, import data, and configure email settings.
    5.  Rendering the **Release Notes** section to inform users about application updates.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    # Fetch all tanks from the database to populate the tank selector
    tanks = TankRepository().fetch_all()
    
    # Create a map of tank IDs to their names and volumes for easy access
    # Using TankRecord to provide more specific type hinting for tank details
    tank_map: Dict[int, TankRecord] = { # Refined type hint
        t["id"]: TankRecord(name=t["name"], volume_l=t.get("volume_l", 0.0)) # Cast to TankRecord
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