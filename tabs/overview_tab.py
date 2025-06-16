# aqualog/tabs/overview_tab.py (Updated)
"""
Overview dashboard — multi-tank aware 🏠

- Displays data for the tank selected in the sidebar.
- Latest-test preview is Arrow-safe
- Trend chart uses Arrow-safe dataframe
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import altair as alt

# 1. Import repositories instead of legacy functions
from aqualog_db.repositories import TankRepository
from aqualog_db.base import BaseRepository

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
    
    # Get the currently selected tank ID from the session state (set by the sidebar)
    selected_tank_id = st.session_state.get("tank_id", 0)

    # 2. Instantiate the repository and call its method
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    
    # Get the name of the selected tank for the header
    tank_name = "Overview"
    if tanks and selected_tank_id:
        # Create a mapping from ID to name
        tank_names = {t["id"]: t["name"] for t in tanks}
        tank_name = tank_names.get(selected_tank_id, "Overview")

    st.header(f"🏠 Overview for: {tank_name}")

    # Handle case where no tank is selected or exists
    if not selected_tank_id:
        st.info("Please add and/or select a tank from the sidebar to see an overview.")
        return

    # ── Latest test (single row) ────────────────────────────────────────────
    with BaseRepository()._connection() as conn:
        df_latest = pd.read_sql_query(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;",
            conn,
            params=(selected_tank_id,),
        )

    if df_latest.empty:
        st.info("No water tests available for this tank.")
        return

    st.subheader("Latest Water Test")
    st.dataframe(arrow_safe(df_latest), use_container_width=True)

    # Out-of-range banner (banner itself figures out breaches)
    show_out_of_range_banner()

    # ── Parameter trends ────────────────────────────────────────────────────
    with BaseRepository()._connection() as conn:
        df_all = pd.read_sql_query(
            """
            SELECT date, ph, ammonia, nitrite, nitrate
            FROM water_tests
            WHERE tank_id = ?
            ORDER BY date;
            """,
            conn,
            params=(selected_tank_id,),
            parse_dates=["date"],
        )

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