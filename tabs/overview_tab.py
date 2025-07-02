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
from datetime import datetime, time # Corrected import: import datetime class and time class
from typing import List, Optional, TYPE_CHECKING 

# --- Import Repositories (runtime imports) ---
from aqualog_db.repositories import TankRepository, WaterTestRepository

# --- Conditional Imports for Type Checking Only ---
if TYPE_CHECKING:
    from aqualog_db.repositories.tank import TankRecord
    from aqualog_db.repositories.water_test import WaterTestRecord

# --- Import Utilities and Config ---
from utils import (
    arrow_safe,
    is_mobile,
    show_toast,
    translate,
    format_with_units,
    is_out_of_range,
)
from config import SAFE_RANGES, TOO_LOW_THRESHOLDS, TOO_HIGH_THRESHOLDS

def overview_tab() -> None:
    """
    Renders the redesigned "Overview" dashboard tab for the currently selected aquarium tank.
    """
    selected_tank_id = st.session_state.get("tank_id", 0)

    # --- Instantiate Repositories ---
    tank_repo = TankRepository()
    water_test_repo = WaterTestRepository()

    tanks = tank_repo.fetch_all() # type: List[TankRecord]
    tank_name = "Overview"
    if tanks and selected_tank_id:
        tank_names = {t["id"]: t["name"] for t in tanks}
        tank_name = tank_names.get(selected_tank_id, "Overview")

    st.header(f"🏠 Tank Overview: {tank_name}")

    if not selected_tank_id:
        st.info("Please select a tank from the sidebar to see an overview.")
        return

    latest_test = water_test_repo.get_latest_for_tank(selected_tank_id) # type: Optional[WaterTestRecord]

    if not latest_test:
        st.info("No water tests available for this tank. Please log a new water test to see the latest results.")
        return
        
    # --- Section 1: At-a-Glance Key Metrics (Latest Test) ---
    st.subheader("Current Water Parameters")
    
    # Display the date and time of the latest test prominently
    test_date_time_obj = datetime.fromisoformat(latest_test['date']) # Corrected usage here
    test_time_for_co2 = test_date_time_obj.time()
    st.markdown(f"Last updated: **{test_date_time_obj.strftime('%Y-%m-%d %H:%M %p')}**")

    # Parameters to display as metrics
    metrics_params = ["ph", "ammonia", "nitrite", "nitrate", "temperature", "kh", "gh"]
    if tank_repo.get_by_id(selected_tank_id).get("has_co2", True):
        metrics_params.append("co2_indicator")
    
    cols = st.columns(4)
    out_of_range_found = False

    for i, param in enumerate(metrics_params):
        value = latest_test.get(param)
        
        with cols[i % 4]:
            if value is not None:
                is_o_o_r = is_out_of_range(
                    param,
                    value,
                    tank_id=selected_tank_id,
                    ph=latest_test.get("ph"),
                    temp_c=latest_test.get("temperature"),
                    test_time=test_time_for_co2
                )
                
                delta_message = "Within Range"
                delta_color = "normal"
                
                if is_o_o_r:
                    out_of_range_found = True
                    delta_color = "inverse"
                    if param == "co2_indicator":
                         if isinstance(value, str) and "Blue" in value: delta_message = "Too Low"
                         elif isinstance(value, str) and "Yellow" in value: delta_message = "Too High"
                    elif isinstance(value, (int, float)):
                        if param in TOO_LOW_THRESHOLDS and value < SAFE_RANGES.get(param, (float('inf'), float('inf')))[0]:
                            delta_message = "Too Low"
                        elif param in TOO_HIGH_THRESHOLDS and value > SAFE_RANGES.get(param, (float('-inf'), float('-inf')))[1]:
                            delta_message = "Too High"
                
                display_value = format_with_units(value, param) if param != "co2_indicator" else str(value)

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

    st.markdown("---")