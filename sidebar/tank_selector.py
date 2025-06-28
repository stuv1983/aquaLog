# sidebar/tank_selector.py

"""
tank_selector.py – Tank Selection Dropdown

Renders the tank selection dropdown menu at the top of the sidebar. It allows the
user to switch the application's context between different managed aquariums,
ensuring that all displayed data and operations pertain to the selected tank.
"""

from __future__ import annotations # Added for type hinting consistency

import streamlit as st
from typing import Dict, Any # Keep Dict and Any if used elsewhere in the file, otherwise remove unnecessary imports
from aqualog_db.repositories.tank import TankRecord # Import TankRecord TypedDict

def render_tank_selector(tank_map: Dict[int, TankRecord]) -> None: # Updated tank_map type hint
    """
    Renders the tank selection dropdown menu in the Streamlit sidebar.

    This function displays a dropdown that allows the user to select an active tank.
    It manages the `tank_id` in `st.session_state` to ensure the application's
    context (e.g., displayed data, forms) is consistent with the chosen tank.

    Args:
        tank_map (Dict[int, TankRecord]): A dictionary where keys are tank IDs (int)
                                              and values are dictionaries containing tank details,
                                              particularly the 'name' which is used for display
                                              in the selectbox. The `tank_map` dictates the
                                              `options` for the selectbox and provides the
                                              `format_func` for displaying tank names.
                                              Example: `{1: {"name": "Main Tank"}, 2: {"name": "Nano Tank"}}`.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.sidebar.header("Tank Selection")

    if not tank_map:
        # If no tanks are found in the database, display a warning.
        st.sidebar.warning("No tanks found. Please add a tank first in Settings.")
        st.session_state["tank_id"] = 0 # Set tank_id to 0 to indicate no tank selected/available
    else:
        # Initialize or update the 'tank_id' in session state.
        # If 'tank_id' is not set, or if the current 'tank_id' doesn't exist in the map
        # (e.g., tank was deleted), default to the first available tank ID.
        if ("tank_id" not in st.session_state) or (st.session_state["tank_id"] not in tank_map):
            st.session_state["tank_id"] = next(iter(tank_map)) # Set to the first tank ID

        # Render the selectbox for tank selection.
        st.sidebar.selectbox(
            "Select Tank",
            options=list(tank_map.keys()),
            format_func=lambda tid: tank_map[tid]["name"],
            key="tank_id" # This directly updates st.session_state.tank_id
        )