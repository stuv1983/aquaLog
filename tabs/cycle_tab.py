"""
tabs/cycle_tab.py – Manage maintenance cycles (start, complete, cancel)
"""

import datetime
import pandas as pd
import streamlit as st

# Refactored DB imports
from aqualog_db.legacy import (
    fetch_all_tanks,
    start_cycle,
    get_active_cycle,
    complete_cycle,
    cancel_cycle,
)
from aqualog_db.base import BaseRepository

from utils import translate, format_with_units

def cycle_tab() -> None:
    """Render the maintenance cycle tab."""
    st.header("🛠️ Maintenance Cycle")

    tank_id = st.session_state.get("tank_id", 1)
    tanks = fetch_all_tanks()
    tank_options = {t["id"]: t["name"] for t in tanks}
    selected = st.selectbox("Select tank", options=list(tank_options.keys()),
                            format_func=lambda tid: tank_options[tid])

    # Display active cycle if exists
    active = get_active_cycle(selected)
    if active:
        st.subheader("Active Cycle")
        st.write(active)
        if st.button("Complete Cycle"):
            complete_cycle(active["id"])
            st.success("Cycle completed.")
        if st.button("Cancel Cycle"):
            cancel_cycle(active["id"])
            st.warning("Cycle canceled.")
        return

    # Start a new cycle
    st.subheader("Start New Cycle")
    start_date = st.date_input("Start Date", value=datetime.date.today(), key="cycle_start_date")
    notes = st.text_area("Notes (optional)", key="cycle_notes")
    if st.button("Start Cycle"):
        start_cycle(selected, start_date.isoformat(), notes)
        st.success("Cycle started.")
        st.experimental_rerun()

    # Show past cycles
    st.subheader("Past Cycles")
    # Use fetch_data for cycle history if appropriate
    with BaseRepository()._connection() as conn:
        df = pd.read_sql_query(
            "SELECT date, notes FROM cycles WHERE tank_id = ? ORDER BY date DESC;",
            conn, params=(selected,)
        )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No past cycle data available.")
