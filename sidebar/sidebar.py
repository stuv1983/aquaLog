# sidebar/sidebar.py (Updated)

import streamlit as st
from typing import Dict, Any

# 1. Import the repository instead of the legacy function
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
    # 2. Instantiate the repository and call its method
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    
    tank_map: Dict[int, Dict[str, Any]] = {
        t["id"]: {"name": t["name"], "volume": t.get("volume_l", 0.0)}
        for t in tanks
    }

    render_tank_selector(tank_map)
    render_water_test_form(tank_map)
    
    with st.sidebar.expander("⚙️ Settings", expanded=False, icon="💧"):
        render_settings_panel(tank_map)
        
    render_release_notes()