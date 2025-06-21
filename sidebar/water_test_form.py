# sidebar/water_test_form.py

"""
water_test_form.py – Water Test Input Form

Renders the "Log Water Test" form in the sidebar. It handles all user input fields
for water parameters and saves the data to the database via the WaterTestRepository.
It also includes logic for real-time display of calculated KH/GH values.
"""

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
from utils.localization import format_with_units

def render_water_test_form(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """
    Renders the water-test logging form in the Streamlit sidebar.

    This form allows users to input various water parameters (pH, Ammonia, Nitrite,
    Nitrate, KH, GH, CO2 Indicator, Temperature) along with date, time, and notes.
    Upon submission, the data is validated and saved to the database for the
    currently selected tank.

    Args:
        tank_map: A dictionary mapping tank IDs to their details (name, volume).
                  Currently, this specific function does not directly use `tank_map`
                  beyond potentially implicitly getting `tank_id` from session state.
    """
    st.sidebar.header("🔬 Log Water Test")

    # Retrieve the currently selected tank ID from Streamlit's session state
    tank_id = st.session_state.get("tank_id", 0)

    # Conditionally render the form or a message
    if tank_id == 0:
        st.sidebar.info("Please select or add a tank in the 'Settings' panel to log water tests.")
        return # Exit the function if no tank is selected
    
    # The form content is now only rendered if a tank is selected
    with st.sidebar.form("desktop_form"):
        
        # --- Date and Time Inputs ---
        st.write("**Test Date & Time**")
        col1, col2 = st.columns(2)
        with col1:
            # Date picker, defaulting to today
            test_date = st.date_input("Date", value=date.today())
        with col2:
            # Time input, defaulting to the current time
            test_time = st.time_input("Time", value=datetime.now().time())
        # --- End Date and Time Inputs ---

        st.markdown("---") # Separator

        # --- Water Parameter Inputs ---
        # Each input field allows users to enter numeric values for water parameters.
        # min_value and step are set for common ranges.
        ph = st.number_input("pH", min_value=0.0, step=0.1, value=7.6)
        ammonia = st.number_input("Ammonia (ppm)", min_value=0.0, step=0.01, value=0.0)
        nitrite = st.number_input("Nitrite (ppm)", min_value=0.0, step=0.01, value=0.0)
        nitrate = st.number_input("Nitrate (ppm)", min_value=0.0, step=0.1, value=0.0, format="%.1f")
        st.markdown("---")
        
        # KH and GH are typically measured in "drops" using test kits.
        # The actual dKH/dGH value is often equal to the number of drops.
        kh_drops = st.number_input("KH Test Drops", min_value=0, step=1, value=4)
        # Display converted KH value in real-time using localization utility
        st.write(f"Actual KH: **{format_with_units(float(kh_drops), 'kh')}**")

        gh_drops = st.number_input("GH Test Drops", min_value=0, step=1, value=8)
        # Display converted GH value in real-time using localization utility
        st.write(f"Actual GH: **{format_with_units(float(gh_drops), 'gh')}**")

        st.markdown("---")
        
        # CO2 indicator is typically a color (Green, Blue, Yellow)
        co2_color = st.selectbox("CO₂ Indicator", ["Green", "Blue", "Yellow"], index=0)
        temperature = st.number_input("Temperature (°C)", min_value=0.0, step=0.5, value=26.0)
        notes = st.text_area("Notes (optional)", "") # Optional text area for additional notes
        
        # --- Form Submission ---
        if st.form_submit_button("💾 Save Test"):
            # Combine the selected date and time into a single datetime object
            combined_datetime = datetime.combine(test_date, test_time)

            # Prepare data dictionary for the WaterTestRepository
            data = {
                # Use the combined datetime for the 'date' field, formatted to seconds precision
                "date": combined_datetime.isoformat(timespec="seconds"),
                "ph": ph,
                "ammonia": ammonia,
                "nitrite": nitrite,
                "nitrate": nitrate,
                "kh": float(kh_drops), # Ensure KH is stored as float
                "gh": float(gh_drops), # Ensure GH is stored as float
                "co2_indicator": co2_color,
                "temperature": temperature,
                "notes": notes,
            }
            try:
                repo = WaterTestRepository()
                repo.save(data, tank_id) # Save data via the repository
                st.sidebar.success("✅ Water test saved!") # Success message in sidebar
                show_toast("Test Saved", "Your readings were successfully recorded.") # Toast notification
                # A rerun might be triggered automatically by Streamlit due to session state changes
                # or could be explicitly called if needed to update other parts of the UI.
            except ValueError as exc:
                st.sidebar.error(f"❌ Failed to save test due to invalid input: {exc}")
            except Exception as exc:
                st.sidebar.error(f"❗ Failed to save test due to an unexpected error: {exc}")