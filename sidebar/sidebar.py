"""
sidebar.py – Refactored Multi-tank Sidebar UI (v4.1)

Key changes:
- Removed clear tests functionality (now handled in settings panel)
- Simplified component structure
- Ensured all imports are relative
- Added proper type hints
"""

import streamlit as st
from typing import Dict, Any

from legacy import fetch_all_tanks
from .tank_selector import render_tank_selector
from .water_test_form import render_water_test_form
from .settings_panel import render_settings_panel
from .release_notes import render_release_notes

def sidebar_entry() -> None:
    """
    Assemble and render the complete sidebar UI.
    
    Organizes components in this order:
    1. Tank selection dropdown
    2. Water test form
    3. Settings panel (contains clear tests functionality)
    4. Release notes
    """
    # Fetch tank data once and pass to components
    tanks = fetch_all_tanks()
    tank_map: Dict[int, Dict[str, Any]] = {
        t["id"]: {
            "name": t["name"],
            "volume": t.get("volume_l", 0.0)
        }
        for t in tanks
    }

    # 1. Tank selector
    render_tank_selector(tank_map)

    # 2. Water test logging form
    render_water_test_form(tank_map)

    # 3. Settings panel (contains clear tests functionality)
    with st.sidebar.expander("⚙️ Settings", expanded=False):
        render_settings_panel(tank_map)

    # 4. Release notes
    render_release_notes()
