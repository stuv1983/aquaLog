# tabs/overview_tab.py

"""
overview_tab.py – Main "Overview" Dashboard

Renders the primary dashboard tab. This view provides a quick summary of the
selected tank's current state, including the most recent water test results
and a trend chart for key parameters.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
import altair as alt
import datetime

# --- Import Repositories ---
from aqualog_db.repositories import TankRepository, WaterTestRepository

# --- Import Utilities ---
from utils import (
    arrow_safe,
    is_mobile,
    show_out_of_range_banner,
    translate,
    format_with_units,
)

print(">>> LOADING", __file__)

# ─────────────────────────────────────────────────────────────────────────────
def render_overview_tab() -> None:
    """Render the Overview dashboard for the currently selected tank."""
    
    selected_tank_id = st.session_state.get("tank_id", 0)

    # --- Instantiate Repositories ---
    tank_repo = TankRepository()
    water_test_repo = WaterTestRepository()

    tanks = tank_repo.fetch_all()
    tank_name = "Overview"
    if tanks and selected_tank_id:
        tank_names = {t["id"]: t["name"] for t in tanks}
        tank_name = tank_names.get(selected_tank_id, "Overview")

    st.header(f"🏠 Overview for: {tank_name}")

    if not selected_tank_id:
        st.info("Please add and/or select a tank from the sidebar to see an overview.")
        return

    # --- Fetch latest test using the repository ---
    latest_test = water_test_repo.get_latest_for_tank(selected_tank_id)

    if not latest_test:
        st.info("No water tests available for this tank.")
        return
        
    df_latest = pd.DataFrame([latest_test])

    st.subheader("Latest Water Test")
    st.dataframe(arrow_safe(df_latest), use_container_width=True)

    show_out_of_range_banner()

    # --- Fetch all tests for trends chart using the repository ---
    start_date = "1970-01-01T00:00:00"
    end_date = datetime.datetime.now().isoformat()
    
    df_all_tests = water_test_repo.fetch_by_date_range(
        start=start_date,
        end=end_date,
        tank_id=selected_tank_id
    )
    
    # Select only the columns needed for the chart
    df_all = df_all_tests[['date', 'ph', 'ammonia', 'nitrite', 'nitrate']].copy()
    
    df_all = arrow_safe(df_all)

    chart = (
        alt.Chart(df_all)
        .transform_fold(
            ["ph", "ammonia", "nitrite", "nitrate"],
            as_=["parameter", "value"],
        )
        .mark_line(point=True)
        .encode(
            x="date:T",
            y="value:Q",
            color="parameter:N",
        )
        .properties(title="Parameter Trends Over Time", height=300)
    )

    st.altair_chart(chart, use_container_width=True)


# Alias for dynamic import
overview_tab = render_overview_tab