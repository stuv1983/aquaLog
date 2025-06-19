# tabs/overview_tab.py

"""
overview_tab.py – Main "Overview" Dashboard

Renders the primary dashboard tab. This view provides a quick summary of the
selected tank's current state, including the most recent water test results
and a trend chart for key parameters (pH, Ammonia, Nitrite, Nitrate).
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
import altair as alt
import datetime

# --- Import Repositories ---
from aqualog_db.repositories import TankRepository, WaterTestRepository #

# --- Import Utilities ---
from utils import (
    arrow_safe, #
    is_mobile, #
    show_out_of_range_banner, #
    translate, #
    format_with_units, #
)

print(">>> LOADING", __file__)

# ─────────────────────────────────────────────────────────────────────────────
def render_overview_tab() -> None:
    """
    Renders the "Overview" dashboard tab for the currently selected aquarium tank.

    This function displays:
    1. The selected tank's name in the header.
    2. The latest recorded water test results in a DataFrame.
    3. A warning banner if any recent parameters are out-of-range.
    4. A time-series chart showing trends for key nitrogen cycle parameters
       (pH, Ammonia, Nitrite, Nitrate).
    If no tank is selected or no data is available, it provides informative messages.
    """
    
    # Retrieve the currently selected tank ID from Streamlit's session state, defaulting to 0.
    selected_tank_id = st.session_state.get("tank_id", 0)

    # --- Instantiate Repositories ---
    tank_repo = TankRepository() #
    water_test_repo = WaterTestRepository() #

    # Determine the tank's name for display in the header.
    tanks = tank_repo.fetch_all() #
    tank_name = "Overview" # Default name if no tank is selected
    if tanks and selected_tank_id:
        # Create a mapping from tank ID to tank name.
        tank_names = {t["id"]: t["name"] for t in tanks}
        # Get the actual name for the selected tank.
        tank_name = tank_names.get(selected_tank_id, "Overview")

    st.header(f"🏠 Overview for: {tank_name}")

    if not selected_tank_id:
        st.info("Please add and/or select a tank from the sidebar to see an overview.")
        return

    # --- Fetch latest water test for the selected tank using the repository ---
    latest_test = water_test_repo.get_latest_for_tank(selected_tank_id) #

    if not latest_test:
        st.info("No water tests available for this tank. Please log a new water test to see the latest results.")
        return
        
    # Convert the single latest test record into a DataFrame for display.
    df_latest = pd.DataFrame([latest_test])

    st.subheader("Latest Water Test")
    # Display the latest test data. `arrow_safe` ensures compatibility with Streamlit's Arrow serialization.
    st.dataframe(arrow_safe(df_latest), use_container_width=True) #

    # Show a banner if any parameters in the latest test are out of range.
    show_out_of_range_banner() #

    # --- Fetch all tests for trends chart using the repository ---
    # Define a wide date range to fetch all historical data for charting trends.
    start_date = "1970-01-01T00:00:00"
    end_date = datetime.datetime.now().isoformat()
    
    # Fetch all water test data for the selected tank.
    df_all_tests = water_test_repo.fetch_by_date_range( #
        start=start_date,
        end=end_date,
        tank_id=selected_tank_id
    )
    
    # Select only the necessary columns for the trend chart.
    df_all = df_all_tests[['date', 'ph', 'ammonia', 'nitrite', 'nitrate']].copy()
    
    # Ensure the 'date' column is in a datetime64[ns] format for Altair/Arrow compatibility.
    df_all = arrow_safe(df_all) #

    # Create the Altair line chart for parameter trends.
    chart = (
        alt.Chart(df_all)
        .transform_fold(
            # "Fold" transforms selected columns (parameters) into two new columns:
            # 'parameter' (name of the original column) and 'value' (its value).
            ["ph", "ammonia", "nitrite", "nitrate"],
            as_=["parameter", "value"],
        )
        .mark_line(point=True) # Draw lines with points at each data point.
        .encode(
            x=alt.X("date:T", title="Date"), # X-axis as a temporal scale.
            y=alt.Y("value:Q", title="Value"), # Y-axis as a quantitative scale.
            color=alt.Color("parameter:N", title="Parameter"), # Color lines by parameter name.
            tooltip=["date:T", "parameter:N", alt.Tooltip("value:Q", format=".2f")], # Tooltip on hover.
        )
        .properties(title="Parameter Trends Over Time", height=300) # Chart title and height.
    )

    st.altair_chart(chart, use_container_width=True) # Render the chart in Streamlit.


# Alias the function for dynamic import, as seen in main.py.
overview_tab = render_overview_tab