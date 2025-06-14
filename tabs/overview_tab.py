# aqualog/tabs/overview_tab.py
"""
Overview dashboard — multi-tank aware 🏠

•   Latest-test preview is Arrow-safe
•   Trend chart uses Arrow-safe dataframe
•   Calls show_out_of_range_banner() with no args
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import altair as alt

from aqualog_db.base   import BaseRepository
from aqualog_db.legacy import fetch_all_tanks

from utils import (
    arrow_safe,                       # 🔸 Arrow compatibility helper
    is_mobile,
    show_out_of_range_banner,
    translate,
    format_with_units,
)

print(">>> LOADING", __file__)

# ─────────────────────────────────────────────────────────────────────────────
def render_overview_tab() -> None:
    """Render the Overview dashboard."""
    st.header("🏠 Overview")

    # ── Tank selector ───────────────────────────────────────────────────────
    tanks = fetch_all_tanks()
    tank_options = {t["id"]: t["name"] for t in tanks}
    selected_tank = st.selectbox(
        "Select tank",
        options=list(tank_options.keys()),
        format_func=lambda tid: tank_options[tid],
    )

    # ── Latest test (single row) ────────────────────────────────────────────
    with BaseRepository()._connection() as conn:
        df_latest = pd.read_sql_query(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;",
            conn,
            params=(selected_tank,),
        )

    if df_latest.empty:
        st.info("No water tests available for this tank.")
        return

    st.subheader("Latest Water Test")
    st.dataframe(arrow_safe(df_latest), use_container_width=True)  # ✔ Arrow-safe

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
            params=(selected_tank,),
            parse_dates=["date"],          # already datetime64[ns]
        )

    df_all = arrow_safe(df_all)            # safety no-op here, but consistent

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
