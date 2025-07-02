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
from aqualog_db.repositories.tank import TankRecord
from aqualog_db.repositories.water_test import WaterTestRecord

from utils import (
    show_toast,
    show_out_of_range_banner,
    arrow_safe,
)
from utils.localization import format_with_units
from components import tooltips

def render_water_test_form(tank_map: Dict[int, TankRecord]) -> None:
    """
    Renders the water-test logging form in the Streamlit sidebar.

    This form allows users to input various water parameters (pH, Ammonia, Nitrite,
    Nitrate, KH, GH, CO2 Indicator, Temperature) along with date, time, and notes.
    Upon submission, the data is validated and saved to the database for the
    currently selected tank.

    Args:
        tank_map (Dict[int, TankRecord]): A dictionary mapping tank IDs to their details
                                             (e.g., name, volume). Used implicitly to determine
                                             the context of the currently selected tank.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.sidebar.header("🔬 Log Water Test")

    # Retrieve the currently selected tank ID from Streamlit's session state.
    tank_id = st.session_state.get("tank_id", 0)

    # Conditionally render the form or a message
    if tank_id == 0:
        st.sidebar.info("Please select or add a tank in the 'Settings' panel to log water tests.")
        return
    
    # The form content is now only rendered if a tank is selected
    with st.sidebar.form("desktop_form"):
        
        # --- Date and Time Inputs ---
        st.write("**Test Date & Time**")
        col1, col2 = st.columns(2)
        with col1:
            # Date picker, defaulting to today
            test_date = st.date_input("Date", value=date.today())
        with col2:
            if "water_test_time_input_value" not in st.session_state:
                st.session_state["water_test_time_input_value"] = datetime.now().time()

            test_time = st.time_input(
                "Time",
                value=st.session_state["water_test_time_input_value"],
                key="test_time_input"
            )
        # --- End Date and Time Inputs ---

        st.markdown("---") # Separator

        # --- Water Parameter Inputs ---
        ph = st.number_input("pH", min_value=0.0, step=0.1, value=7.6, help=tooltips.get("pH"))
        ammonia = st.number_input("Ammonia (ppm)", min_value=0.0, step=0.01, value=0.0, help=tooltips.get("ammonia"))
        nitrite = st.number_input("Nitrite (ppm)", min_value=0.0, step=0.01, value=0.0, help=tooltips.get("nitrite"))
        nitrate = st.number_input("Nitrate (ppm)", min_value=0.0, step=0.1, value=0.0, format="%.1f", help=tooltips.get("nitrate"))
        st.markdown("---")
        
        kh_drops = st.number_input("KH Test Drops", min_value=0, step=1, value=4, help=tooltips.get("kh"))
        st.write(f"Actual KH: **{format_with_units(float(kh_drops), 'kh')}**")

        gh_drops = st.number_input("GH Test Drops", min_value=0, step=1, value=8, help=tooltips.get("gh"))
        st.write(f"Actual GH: **{format_with_units(float(gh_drops), 'gh')}**")

        st.markdown("---")
        
        tank_has_co2 = tank_map.get(tank_id, {}).get("has_co2", True)
        if tank_has_co2:
            co2_color = st.selectbox("CO₂ Indicator", ["Green", "Blue", "Yellow"], index=0, help=tooltips.get("co2"))
        else:
            co2_color = None
        
        temperature = st.number_input("Temperature (°C)", min_value=0.0, step=0.5, value=26.0, help=tooltips.get("temperature"))
        notes = st.text_area("Notes (optional)", "")
        
        # --- Form Submission ---
        if st.form_submit_button("💾 Save Test"):
            # Update the session state with the time selected by the user before saving
            st.session_state["water_test_time_input_value"] = test_time

            # Combine the selected date and time into a single datetime object
            combined_datetime = datetime.combine(test_date, test_time)

            # Prepare data dictionary for the WaterTestRepository
            data: WaterTestRecord = {
                "date": combined_datetime.isoformat(timespec="seconds"),
                "ph": ph,
                "ammonia": ammonia,
                "nitrite": nitrite,
                "nitrate": nitrate,
                "kh": float(kh_drops),
                "gh": float(gh_drops),
                "co2_indicator": co2_color,
                "temperature": temperature,
                "notes": notes,
            }
            try:
                repo = WaterTestRepository()
                repo.save(data, tank_id)
                st.sidebar.success("✅ Water test saved!")
                show_toast("Test Saved", "Your readings were successfully recorded.")
            except ValueError as exc:
                st.sidebar.error(f"❌ Failed to save test due to invalid input: {exc}")
            except Exception as exc:
                st.sidebar.error(f"❗ Failed to save test due to an unexpected error: {exc}")