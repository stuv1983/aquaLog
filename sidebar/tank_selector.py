import streamlit as st
from typing import Dict, Any

def render_tank_selector(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the tank selection dropdown."""
    st.sidebar.header("Tank Selection")

    if not tank_map:
        st.sidebar.warning("No tanks found. Please add a tank first in Settings.")
        st.session_state["tank_id"] = 0
    else:
        if ("tank_id" not in st.session_state) or (st.session_state["tank_id"] not in tank_map):
            st.session_state["tank_id"] = next(iter(tank_map))

        st.sidebar.selectbox(
            "Select Tank",
            options=list(tank_map.keys()),
            format_func=lambda tid: tank_map[tid]["name"],
            key="tank_id"
        )
