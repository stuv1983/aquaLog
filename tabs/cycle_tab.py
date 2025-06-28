# tabs/cycle_tab.py

"""
cycle_tab.py – Nitrogen Cycle Tracker

Renders the "Cycle" tab. This view visualizes the progression of ammonia,
nitrite, and nitrate levels over time to help users monitor the establishment
of their tank's biological filter. It also provides an assessment of whether
the tank appears to be fully cycled based on recent test results.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
import altair as alt
import datetime

# --- Import Repositories ---
from aqualog_db.repositories import TankRepository, WaterTestRepository
from config import SAFE_RANGES

def _is_tank_cycled(df: pd.DataFrame) -> bool:
    """
    Determines if a tank is considered "cycled" based on the last 3 water test
    results for ammonia, nitrite, and nitrate.

    A tank is considered cycled if:
    1. There are at least 3 historical test records.
    2. Ammonia levels have been at or below the safe limit (typically 0 ppm)
       for the last 3 tests.
    3. Nitrite levels have been at or below the safe limit (typically 0 ppm)
       for the last 3 tests.
    4. Nitrate levels are present (greater than 0 ppm) in the most recent test.

    Args:
        df (pd.DataFrame): A Pandas DataFrame containing water test history for a single tank.
                           It must be sorted by date in ascending order and
                           **must include** 'ammonia', 'nitrite', and 'nitrate' columns.

    Returns:
        bool: True if the tank meets the criteria for being cycled, False otherwise.
    """
    # A minimum of 3 tests are needed for a confident assessment of cycling.
    if len(df) < 3:
        return False

    # Get the last 3 test results for analysis.
    recent_tests = df.tail(3)

    # Get safe upper limits for ammonia and nitrite from configuration.
    # These are typically 0 ppm for a cycled tank.
    ammonia_safe_high = SAFE_RANGES.get("ammonia", (0, 0))[1]
    nitrite_safe_high = SAFE_RANGES.get("nitrite", (0, 0))[1]

    # Check if Ammonia has been at or below its safe limit for all last 3 tests.
    ammonia_cycled = (recent_tests['ammonia'] <= ammonia_safe_high).all()
    # Check if Nitrite has been at or below its safe limit for all last 3 tests.
    nitrite_cycled = (recent_tests['nitrite'] <= nitrite_safe_high).all()

    # Get the very last test to check for the presence of nitrates.
    # Nitrates indicate that the nitrification process is complete.
    last_test = df.iloc[-1]
    nitrate_present = last_test['nitrate'] > 0

    # The tank is considered cycled if both ammonia and nitrite are consistently low
    # and nitrates are being produced.
    return ammonia_cycled and nitrite_cycled and nitrate_present


def cycle_tab(key_prefix: str = "") -> None:
    """
    Renders the "Nitrogen Cycle Tracker" tab in the Streamlit application.

    This tab displays:
    1.  The currently selected tank's name and a general cycle status message.
    2.  An interactive line chart visualizing the historical trends of ammonia,
        nitrite, and nitrate levels over time.
    3.  Educational content on how to interpret the nitrogen cycle chart.
    4.  A raw data table showing the historical cycle-related water test data.

    Args:
        key_prefix (str): A string prefix for Streamlit widget keys to ensure uniqueness
                          when this tab might be rendered multiple times or dynamically.
                          Defaults to an empty string.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.header("🔄 Nitrogen Cycle Tracker")

    # Retrieve the currently selected tank ID from Streamlit's session state.
    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank to view its cycle progress.")
        return
        
    # --- Instantiate Repositories ---
    tank_repo = TankRepository()
    water_test_repo = WaterTestRepository()

    # Get tank name for display.
    tanks = tank_repo.fetch_all()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")
    st.info(f"Showing cycle progress for: **{tank_name}**")

    # --- Fetch all relevant water test data for the selected tank ---
    # Fetch all data from the beginning of time (1970-01-01) until today.
    start_date = "1970-01-01T00:00:00"
    end_date = datetime.datetime.now().isoformat()
    
    all_tests_df = water_test_repo.fetch_by_date_range(
        start=start_date,
        end=end_date,
        tank_id=tank_id
    )

    # 2. Handle the case where there is no data for the selected tank.
    if all_tests_df.empty:
        st.info("No water test data available for this tank. Log tests with ammonia, nitrite, and nitrate values to track the cycle.")
        return

    # Select only the relevant columns for cycle tracking.
    # Create a copy to avoid SettingWithCopyWarning.
    df = all_tests_df[['date', 'ammonia', 'nitrite', 'nitrate']].copy()

    # 3. Check if the tank is cycled and display a status message.
    if _is_tank_cycled(df):
        st.success("🎉 Congratulations! This tank appears to be cycled. Ammonia and Nitrite have been at zero in recent tests while Nitrates are present.")
    else:
        st.info("The nitrogen cycle is still establishing or needs attention. Monitor ammonia and nitrite levels closely.")


    # 4. Create an interactive line chart with Altair to visualize parameter trends.
    st.subheader("Parameter Trends Over Time")

    # Melt the DataFrame from wide to long format.
    # This is necessary for Altair to easily assign 'Parameter' to color and 'Concentration (ppm)' to Y-axis.
    df_melted = df.melt('date', var_name='Parameter', value_name='Concentration (ppm)')

    chart = alt.Chart(df_melted).mark_line(point=True).encode(
        x=alt.X('date:T', title='Date'), # Time-series axis
        y=alt.Y('Concentration (ppm):Q', title='Concentration (ppm)'), # Quantitative axis
        color=alt.Color('Parameter:N', title='Parameter'), # Nominal data for coloring different lines
        tooltip=['date:T', 'Parameter:N', alt.Tooltip('Concentration (ppm):Q', format='.2f')]
    ).properties(
        title="Nitrogen Cycle Progress"
    ).interactive() # Make the chart interactive (zoom, pan).

    st.altair_chart(chart, use_container_width=True) # Render the chart in Streamlit.

    # 5. Provide instructions and educational content on how to interpret the chart.
    with st.expander("How to Interpret This Chart"):
        st.markdown("""
            The nitrogen cycle is established when beneficial bacteria convert toxic compounds into safer ones. Look for this pattern in the chart:
            - **Ammonia (NH₃)** will spike first as waste breaks down.
            - **Nitrite (NO₂)** will rise as bacteria consume the ammonia.
            - **Nitrate (NO₃)** will begin to appear as other bacteria consume the nitrite.

            A fully cycled tank will show consistent readings of **0 ppm Ammonia** and **0 ppm Nitrite**, with a steady (but manageable) level of Nitrates.
        """)

    # 6. Display the raw data in a sortable table for detailed review.
    st.subheader("Cycle Data History")
    st.dataframe(
        df.sort_values(by="date", ascending=False), # Show most recent tests first
        column_config={
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "ammonia": st.column_config.NumberColumn("Ammonia (ppm)", format="%.2f"),
            "nitrite": st.column_config.NumberColumn("Nitrite (ppm)", format="%.2f"),
            "nitrate": st.column_config.NumberColumn("Nitrate (ppm)", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )