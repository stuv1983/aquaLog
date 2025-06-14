"""
tabs/cycle_tab.py – Nitrogen Cycle Tracker 📈

Displays a chart of ammonia, nitrite, and nitrate levels over time for the
selected tank to visualize the progress of the aquarium's nitrogen cycle.
Includes a check to determine if the cycle is complete.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import altair as alt

from aqualog_db.connection import get_connection
from aqualog_db.legacy import fetch_all_tanks
from config import SAFE_RANGES

def _is_tank_cycled(df: pd.DataFrame) -> bool:
    """
    Determines if a tank is cycled based on the last 3 water tests.

    Args:
        df: A DataFrame with water test history, sorted by date.

    Returns:
        True if the tank is considered cycled, False otherwise.
    """
    # A minimum of 3 tests are needed for a confident assessment.
    if len(df) < 3:
        return False

    # Get the last 3 test results.
    recent_tests = df.tail(3)

    # Get safe levels from config. Nitrite/Ammonia should be 0.
    ammonia_safe_high = SAFE_RANGES.get("ammonia", (0, 0))[1]
    nitrite_safe_high = SAFE_RANGES.get("nitrite", (0, 0))[1]

    # Check if Ammonia and Nitrite have been at or below the safe level for the last 3 tests.
    ammonia_cycled = (recent_tests['ammonia'] <= ammonia_safe_high).all()
    nitrite_cycled = (recent_tests['nitrite'] <= nitrite_safe_high).all()

    # Check if some nitrates are present in the most recent test.
    last_test = df.iloc[-1]
    nitrate_present = last_test['nitrate'] > 0

    return ammonia_cycled and nitrite_cycled and nitrate_present


def cycle_tab(key_prefix=""):
    """Render the Nitrogen Cycle tracker tab."""
    st.header("🔄 Nitrogen Cycle Tracker")

    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank to view its cycle progress.")
        return
        
    tanks = fetch_all_tanks()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")
    st.info(f"Showing cycle progress for: **{tank_name}**")

    # 1. Fetch all relevant water tests for the selected tank
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT date, ammonia, nitrite, nitrate
            FROM water_tests
            WHERE tank_id = ?
            ORDER BY date;
            """,
            conn,
            params=(tank_id,),
            parse_dates=["date"],
        )

    # 2. Handle the case where there is no data
    if df.empty:
        st.info("No water test data available for this tank. Log tests with ammonia, nitrite, and nitrate values to track the cycle.")
        return

    # 3. Check if the tank is cycled and display a status message
    if _is_tank_cycled(df):
        st.success("🎉 Congratulations! This tank appears to be cycled. Ammonia and Nitrite have been at zero in recent tests while Nitrates are present.")

    # 4. Create an interactive line chart with Altair
    st.subheader("Parameter Trends Over Time")

    # Melt the dataframe to make it suitable for Altair's color encoding
    df_melted = df.melt('date', var_name='Parameter', value_name='Concentration (ppm)')

    chart = alt.Chart(df_melted).mark_line(point=True).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('Concentration (ppm):Q', title='Concentration (ppm)'),
        color=alt.Color('Parameter:N', title='Parameter'),
        tooltip=['date:T', 'Parameter:N', alt.Tooltip('Concentration (ppm):Q', format='.2f')]
    ).properties(
        title="Nitrogen Cycle Progress"
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    # 5. Provide instructions on how to interpret the chart
    with st.expander("How to Interpret This Chart"):
        st.markdown("""
            The nitrogen cycle is established when beneficial bacteria convert toxic compounds into safer ones. Look for this pattern in the chart:
            - **Ammonia (NH₃)** will spike first as waste breaks down.
            - **Nitrite (NO₂)** will rise as bacteria consume the ammonia.
            - **Nitrate (NO₃)** will begin to appear as other bacteria consume the nitrite.

            A fully cycled tank will show consistent readings of **0 ppm Ammonia** and **0 ppm Nitrite**, with a steady (but manageable) level of Nitrates.
        """)

    # 6. Display the raw data in a table
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