# sidebar/tank_selector.py

"""
tank_selector.py – Tank Selection Dropdown

Renders the tank selection dropdown menu at the top of the sidebar. It allows the
user to switch the application's context between different managed aquariums,
ensuring that all displayed data and operations pertain to the selected tank.
"""

import streamlit as st
from typing import Dict, Any

def render_tank_selector(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """
    Renders the tank selection dropdown menu in the Streamlit sidebar.

    This function displays a dropdown that allows the user to select an active tank.
    It manages the `tank_id` in `st.session_state` to ensure the application's
    context (e.g., displayed data, forms) is consistent with the chosen tank.

    Args:
        tank_map: A dictionary where keys are tank IDs (int) and values are
                  dictionaries containing tank details, particularly the 'name'
                  which is used for display in the selectbox.
                  Example: `{1: {"name": "Main Tank"}, 2: {"name": "Nano Tank"}}`
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
        # `options`: List of tank IDs (integer keys from tank_map).
        # `format_func`: A lambda function to display tank names instead of IDs in the dropdown.
        # `key`: Unique key for this widget to persist its value in session state.
        st.sidebar.selectbox(
            "Select Tank",
            options=list(tank_map.keys()),
            format_func=lambda tid: tank_map[tid]["name"],
            key="tank_id" # This directly updates st.session_state.tank_id
        )