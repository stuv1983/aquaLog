# tabs/overview_tab.py

"""
overview_tab.py – Main "Overview" Dashboard Redesign

Renders the primary dashboard tab with a focus on immediate insights.
Displays key metrics using st.metric cards, highlights out-of-range parameters
with direct calls to action. Historical trends are now exclusively in the
Data & Analytics tab.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
import datetime

# --- Import Repositories ---
from aqualog_db.repositories import TankRepository, WaterTestRepository #

# --- Import Utilities and Config ---
from utils import (
    arrow_safe, #
    is_mobile, #
    show_toast, # Not directly used but good for UI feedback if needed
    translate, #
    format_with_units, #
    is_out_of_range, # Crucial for checking parameter status
)
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS # Used for status logic

def render_overview_tab() -> None:
    """
    Renders the redesigned "Overview" dashboard tab for the currently selected aquarium tank.

    This function displays:
    1. The selected tank's name in the header.
    2. Key water test metrics (pH, Ammonia, Nitrite, Nitrate, Temperature, KH, GH)
       using st.metric cards with visual indicators for in-range/out-of-range status.
    3. A clear warning message and call to action if any parameters are out of range.
    4. An expandable section to view the raw data of the latest water test.
    """
    
    # Debugging line: Check the current tank ID at the start of the tab rendering
    selected_tank_id = st.session_state.get("tank_id", 0)
    st.write(f"Debugging: Current Tank ID in Overview Tab: {selected_tank_id}") # Debugging line
    

    # --- Instantiate Repositories ---
    tank_repo = TankRepository() #
    water_test_repo = WaterTestRepository() #

    # Get tank name for display.
    tanks = tank_repo.fetch_all() #
    tank_name = "Overview" # Default name if no tank is selected
    if tanks and selected_tank_id:
        tank_names = {t["id"]: t["name"] for t in tanks}
        tank_name = tank_names.get(selected_tank_id, "Overview")

    st.header(f"🏠 Tank Overview: {tank_name}")

    if not selected_tank_id:
        st.info("Please select a tank from the sidebar to see an overview.")
        return

    # Fetch the latest water test for the selected tank.
    latest_test = water_test_repo.get_latest_for_tank(selected_tank_id) #

    if not latest_test:
        st.info("No water tests available for this tank. Please log a new water test to see the latest results.")
        return
        
    # --- Section 1: At-a-Glance Key Metrics (Latest Test) ---
    st.subheader("Current Water Parameters")
    
    # Display the date and time of the latest test prominently
    test_date_time_obj = datetime.datetime.fromisoformat(latest_test['date'])
    st.markdown(f"Last updated: **{test_date_time_obj.strftime('%Y-%m-%d %H:%M %p')}**")

    # Parameters to display as metrics
    metrics_params = ["ph", "ammonia", "nitrite", "nitrate", "temperature", "kh", "gh", "co2_indicator"]
    # Divide into 4 columns per row for better layout
    cols = st.columns(4) 
    out_of_range_found = False

    for i, param in enumerate(metrics_params):
        value = latest_test.get(param)
        
        with cols[i % 4]: # Cycle through columns
            if value is not None:
                # Determine if the parameter is out of its safe range
                is_o_o_r = is_out_of_range(
                    param,
                    value,
                    tank_id=selected_tank_id,
                    ph=latest_test.get("ph"), # Pass pH for ammonia calculation
                    temp_c=latest_test.get("temperature") # Pass temperature for ammonia calculation
                )
                
                delta_message = "Within Range"
                delta_color = "normal" # Green for in range
                
                if is_o_o_r:
                    out_of_range_found = True
                    delta_color = "inverse" # Red for out of range
                    if param == "co2_indicator":
                         if "Blue" in value: delta_message = "Too Low"
                         elif "Yellow" in value: delta_message = "Too High"
                    elif param in TOO_LOW_THRESHOLDS and value < SAFE_RANGES.get(param, (float('inf'), float('inf')))[0]:
                        delta_message = "Too Low"
                    elif param in TOO_HIGH_THRESHOLDS and value > SAFE_RANGES.get(param, (float('-inf'), float('-inf')))[1]:
                        delta_message = "Too High"
                
                # Format value with units, or display as string for CO2 indicator
                display_value = format_with_units(value, param) if param != "co2_indicator" else str(value) #

                st.metric(
                    label=param.capitalize() if param not in ("ph", "kh", "gh") else param.upper(),
                    value=display_value,
                    delta=delta_message,
                    delta_color=delta_color
                )
            else:
                st.metric(label=param.capitalize(), value="N/A", delta="No data", delta_color="off")

    # --- Section 2: Actionable Warning Summary (if any) ---
    if out_of_range_found:
        st.error("🚨 One or more parameters are out of their safe range!", icon="❗")
        st.markdown("For detailed advice and recommended actions, please visit the **Warnings** tab.")
    else:
        st.success("✅ All water parameters are currently within their safe ranges!")


    st.markdown("---") # Visual separator

    # --- Section 3: Raw Data of Latest Test (instead of trends) ---
    # Optional: Expandable section to view raw data table for the latest test only
    with st.expander("Show Raw Data of Latest Test"):
        df_latest_display = pd.DataFrame([latest_test])
        st.dataframe(arrow_safe(df_latest_display), use_container_width=True) #

# Alias the function for dynamic import in main.py.
overview_tab = render_overview_tab