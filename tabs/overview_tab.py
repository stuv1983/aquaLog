import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image

from aqualog_db.base import BaseRepository
from aqualog_db.legacy import fetch_all_tanks
from utils import is_mobile, show_out_of_range_banner, translate, format_with_units
from config import SAFE_RANGES

def render_overview_tab() -> None:
    """
    Render the overview dashboard with key metrics and trends.
    """
    st.header("🏠 Overview")

    # Fetch data
    tanks = fetch_all_tanks()
    tank_options = {t['id']: t['name'] for t in tanks}
    selected_tank = st.selectbox("Select tank", options=list(tank_options.keys()),
                                 format_func=lambda tid: tank_options[tid])

    # Latest test details
    with BaseRepository()._connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1",
            conn, params=(selected_tank,)
        )

    if df.empty:
        st.info("No water tests available for this tank.")
        return

    latest = df.iloc[0]
    st.subheader("Latest Water Test")
    st.write(latest)

    # Out-of-range warning
    show_out_of_range_banner()

    # Time series chart
    with BaseRepository()._connection() as conn:
        df_all = pd.read_sql_query(
            "SELECT date, ph, ammonia, nitrite, nitrate FROM water_tests WHERE tank_id = ?",
            conn, params=(selected_tank,)
        )

    df_all['date'] = pd.to_datetime(df_all['date'])
    chart = alt.Chart(df_all).transform_fold(
        ["ph", "ammonia", "nitrite", "nitrate"],
        as_=["parameter", "value"]
    ).mark_line(point=True).encode(
        x="date:T", y="value:Q", color="parameter:N"
    ).properties(title="Parameter Trends Over Time", height=300)

    st.altair_chart(chart, use_container_width=True)

# Alias for loader
overview_tab = render_overview_tab
