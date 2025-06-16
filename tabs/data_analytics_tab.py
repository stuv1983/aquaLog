# tabs/data_analytics_tab.py (Updated)

"""
tabs/data_analytics_tab.py – multi-tank aware 🎛️

Provides the **Data & Analytics** view with visualisation controls, raw-data
layout, rolling averages, correlation matrix, scatter/regression, basic
forecasting, and full CSV export. All queries are scoped to the **selected tank**.
"""

import datetime
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st
import altair as alt

# 1. Import repositories instead of legacy functions
from aqualog_db.repositories import TankRepository, WaterTestRepository
from aqualog_db.connection import get_connection

from utils import (
    is_mobile,
    clean_numeric_df,
    translate,
    format_with_units,
    is_out_of_range,
)
from config import SAFE_RANGES

def _get_min_max_dates(cur, tank_id: int) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    """Helper to get the min/max dates for a given tank."""
    cur.execute(
        "SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;",
        (tank_id,),
    )
    row = cur.fetchone()
    def _parse(val: str | None) -> Optional[datetime.date]:
        if not val: return None
        try: return datetime.datetime.fromisoformat(val).date()
        except Exception:
            try:
                pd_ts = pd.to_datetime(val, errors="coerce")
                return pd_ts.date() if not pd.isna(pd_ts) else None
            except Exception: return None
    if not row or not row[0]: return None, None
    return _parse(row[0]), _parse(row[1])


def data_analytics_tab() -> None:
    """Render the Data & Analytics tab scoped to the active tank."""
    tank_id: int = st.session_state.get("tank_id", 1)
    
    # 2. Instantiate the repository and call its method
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")

    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    with get_connection() as conn:
        cur = conn.cursor()
        min_date, max_date = _get_min_max_dates(cur, tank_id)

    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}.")
        return

    # Construct start and end strings that include the full day to ensure all data is fetched
    start_str = datetime.datetime.combine(min_date, datetime.time.min).isoformat()
    end_str = datetime.datetime.combine(max_date, datetime.time.max).isoformat()

    # 3. Instantiate the repository and call its method
    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range(start_str, end_str, tank_id)


    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name}.")
        return

    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    numeric_params: List[str] = [c for c in df_clean.columns if c not in ("date", "notes", "id", "tank_id")]
    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name}.")
        return

    # Visualisation controls expander
    with st.expander("🔧 " + translate("Visualisation Controls"), expanded=not is_mobile()):
        date_range = st.date_input(
            translate("Select Date Range"),
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="vis_date_range",
        )
        # Use the date_range from the widget to filter the dataframe for display
        if len(date_range) == 2:
            start_date, end_date = date_range
            if start_date > end_date:
                st.error(translate("Start date must be on or before end date."))
                return
            
            # Filter the already-fetched dataframe based on the user's selection
            vis_df = df_clean[
                (df_clean["date"].dt.date >= start_date) &
                (df_clean["date"].dt.date <= end_date)
            ]
        else:
            vis_df = df_clean # If date range is not set correctly, use all fetched data

        # The rest of the visualisation controls and chart rendering logic...
        param_opts = ["All"] + numeric_params
        selected_params = st.multiselect(
            translate("Choose Parameter(s)"),
            options=param_opts,
            default=["All"],
            key="vis_params"
        )
        if "All" in selected_params or not selected_params:
            params_to_plot = numeric_params
        else:
            params_to_plot = [p for p in selected_params if p in numeric_params]

    # ... (The rest of the tab's logic for charts, tables, etc., would follow)
    # This section is not included as it was not part of the bug fix.
    st.write("---")
    st.write("Chart and analysis sections would be displayed here.")