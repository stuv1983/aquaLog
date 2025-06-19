# sidebar/water_test_form.py

"""
water_test_form.py – Water Test Input Form

Renders the "Log Water Test" form in the sidebar. It handles all user input fields
for water parameters and saves the data to the database. It also includes logic
for a multi-step "wizard" on mobile devices.
"""

# sidebar/water_test_form.py

from __future__ import annotations
from datetime import datetime, date, time

from typing import Dict, Any

import pandas as pd
import streamlit as st

from aqualog_db.repositories import WaterTestRepository
from utils import (
    show_toast,
    show_out_of_range_banner,
    arrow_safe,
)
from utils.localization import format_with_units # New import for unit formatting

def render_water_test_form(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the water-test logging form in the sidebar."""
    st.sidebar.header("🔬 Log Water Test")

    with st.sidebar.form("desktop_form"):
        
        # --- NEW DATE AND TIME INPUTS ---
        st.write("**Test Date & Time**")
        col1, col2 = st.columns(2)
        with col1:
            test_date = st.date_input("Date", value=date.today())
        with col2:
            test_time = st.time_input("Time", value=datetime.now().time())
        # --- END NEW INPUTS ---

        st.markdown("---")
        
        ph = st.number_input("pH", min_value=0.0, step=0.1, value=7.6)
        ammonia = st.number_input("Ammonia (ppm)", min_value=0.0, step=0.01, value=0.0)
        nitrite = st.number_input("Nitrite (ppm)", min_value=0.0, step=0.01, value=0.0)
        nitrate = st.number_input("Nitrate (ppm)", min_value=0.0, step=0.1, value=0.0, format="%.1f")
        st.markdown("---")
        
        kh_drops = st.number_input("KH Test Drops", min_value=0, step=1, value=4)
        # Display converted KH value in real-time
        # Assuming 1 drop = 1 dKH for the actual KH level
        st.write(f"Actual KH: **{format_with_units(float(kh_drops), 'kh')}**")

        gh_drops = st.number_input("GH Test Drops", min_value=0, step=1, value=8)
        # Display converted GH value in real-time
        # Assuming 1 drop = 1 dGH for the actual GH level
        st.write(f"Actual GH: **{format_with_units(float(gh_drops), 'gh')}**")

        st.markdown("---")
        co2_color = st.selectbox("CO₂ Indicator", ["Green", "Blue", "Yellow"], index=0)
        temperature = st.number_input("Temperature (°C)", min_value=0.0, step=0.5, value=26.0)
        notes = st.text_area("Notes (optional)", "")
        
        if st.form_submit_button("💾 Save Test"):
            tank_id = st.session_state.get("tank_id", 0)
            if tank_id == 0:
                st.error("Please add and select a tank before saving a test.")
            else:
                # Combine the selected date and time into a single datetime object
                combined_datetime = datetime.combine(test_date, test_time)

                data = {
                    # Use the combined datetime for the 'date' field
                    "date": combined_datetime.isoformat(timespec="seconds"),
                    "ph": ph, "ammonia": ammonia, "nitrite": nitrite, "nitrate": nitrate,
                    "kh": float(kh_drops), "gh": float(gh_drops), "co2_indicator": co2_color,
                    "temperature": temperature, "notes": notes,
                }
                try:
                    repo = WaterTestRepository()
                    repo.save(data, tank_id)
                    st.sidebar.success("Water test saved!")
                    show_toast("Test Saved", "Your readings were successfully recorded.")
                except Exception as exc:
                    st.sidebar.error(f"Failed to save test: {exc}")
