# tabs/data_analytics_tab.py  (Patched to preserve CO2 indicator in raw data)
"""
tabs/data_analytics_tab.py – multi‑tank aware 🎛️

Provides the **Data & Analytics** view with visualisation controls, raw-data
layout (including string fields like CO2 indicator), rolling averages,
correlation matrix, scatter/regression, and forecasting. All queries scoped
to the **selected tank**.
"""

import datetime
from typing import Optional, Tuple

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from aqualog_db.repositories import TankRepository, WaterTestRepository
from aqualog_db.connection import get_connection

from utils import is_mobile, clean_numeric_df, translate
from config import SAFE_RANGES


def _get_min_max_dates(cur, tank_id: int) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    cur.execute(
        "SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;",
        (tank_id,),
    )
    row = cur.fetchone()
    def _parse(val):
        if not val:
            return None
        try:
            return datetime.datetime.fromisoformat(val).date()
        except Exception:
            ts = pd.to_datetime(val, errors='coerce')
            return ts.date() if not pd.isna(ts) else None
    if not row or not row[0]:
        return None, None
    return _parse(row[0]), _parse(row[1])


def data_analytics_tab() -> None:
    tank_id = st.session_state.get("tank_id", 1)
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t['name'] for t in tanks if t['id'] == tank_id), f"Tank #{tank_id}")
    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    # Fetch available dates
    with get_connection() as conn:
        min_date, max_date = _get_min_max_dates(conn.cursor(), tank_id)
    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}.")
        return

    # Retrieve raw data
    start_iso = datetime.datetime.combine(min_date, datetime.time.min).isoformat()
    end_iso   = datetime.datetime.combine(max_date, datetime.time.max).isoformat()
    df = WaterTestRepository().fetch_by_date_range(start_iso, end_iso, tank_id)
    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name}.")
        return

    # Clean numeric fields & preserve all others (e.g. co2_indicator)
    df_clean = clean_numeric_df(df).dropna(subset=["date"])

    # Identify numeric parameters (exclude IDs)
    numeric_params = df_clean.select_dtypes(include=np.number).columns.tolist()
    numeric_params = [p for p in numeric_params if p not in ['id', 'tank_id']]

    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name}.")
        return

    # --- Visualisation Controls ---
    with st.expander("🔧 " + translate("Visualisation Controls"), expanded=not is_mobile()):
        date_range = st.date_input(
            translate("Select Date Range"),
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="vis_date_range",
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            if start_date > end_date:
                st.error(translate("Start date must be on or before end date."))
                return
            vis_df = df_clean[(df_clean["date"].dt.date >= start_date) & (df_clean["date"].dt.date <= end_date)]
        else:
            vis_df = df_clean

    # --- Raw Data Table (includes CO2 indicator strings) ---
    with st.expander("🗂️ Raw Data Table", expanded=False):
        st.dataframe(vis_df, use_container_width=True)
        csv_bytes = vis_df.to_csv(index=False).encode()
        st.download_button(
            "📥 Download Filtered Data as CSV",
            csv_bytes,
            file_name=f"aqualog_data_{tank_name}_{date_range[0]}_to_{date_range[1]}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # --- 30-Day Rolling Averages ---
    with st.expander("🔄 30-Day Rolling Averages", expanded=False):
        df_idx, rolls = vis_df.set_index("date"), []
        for param in numeric_params:
            ser = df_idx[param].dropna()
            if ser.empty:
                continue
            roll = ser.rolling("30D", min_periods=1).mean().reset_index().rename(columns={param: "value"})
            roll["param"] = param
            rolls.append(roll)
        if rolls:
            chart = (
                alt.Chart(pd.concat(rolls, ignore_index=True))
                .mark_line()
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("value:Q", title="30-Day Avg"),
                    color=alt.Color("param:N", title="Parameter"),
                    tooltip=["date:T","param:N",alt.Tooltip("value:Q",format=".2f")],
                ).properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

    # --- Correlation Matrix ---
    with st.expander("🔗 Correlation Matrix", expanded=False):
        try:
            corr = vis_df[numeric_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception:
            st.error("Unable to compute correlation matrix.")

    # --- Scatter & Regression ---
    with st.expander("🔍 Scatter & Regression", expanded=False):
        xcol = st.selectbox("X-axis", numeric_params, key="scatter_x")
        ycol = st.selectbox("Y-axis", numeric_params, key="scatter_y")
        df_sc = vis_df.dropna(subset=[xcol, ycol])
        if not df_sc.empty:
            scatter = alt.Chart(df_sc).mark_circle(size=60).encode(
                x=alt.X(f"{xcol}:Q", title=xcol),
                y=alt.Y(f"{ycol}:Q", title=ycol),
                tooltip=["date", xcol, ycol],
            )
            reg = scatter.transform_regression(xcol, ycol).mark_line(color="red")
            st.altair_chart(scatter + reg, use_container_width=True)
        else:
            st.write("Not enough data for scatter/regression.")

    # --- 7-Day Forecast ---
    with st.expander("📈 7-Day Forecast", expanded=False):
        opts = ["All"] + numeric_params
        sel = st.multiselect(translate("Forecast parameter(s)"), opts, default=["All"], key="forecast_params")
        to_plot = numeric_params if "All" in sel or not sel else sel
        plots = []
        for param in to_plot:
            series = vis_df.set_index("date")[param].dropna()
            if len(series) < 2:
                continue
            try:
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                forecast = model.forecast(7)
                fut = pd.date_range(series.index.max() + datetime.timedelta(days=1), periods=7, freq="D")
                fc = pd.DataFrame({"date": fut, "value": forecast.values, "type": "forecast", "param": param})
                hist = series.reset_index().rename(columns={param: "value"})
                hist["type"], hist["param"] = "historical", param
                plots.append(hist)
                plots.append(fc)
            except Exception:
                st.warning(f"Could not generate forecast for '{param}'.")
        if plots:
            dfp = pd.concat(plots, ignore_index=True)
            line = alt.Chart(dfp).mark_line().encode(
                x=alt.X("date:T"), y=alt.Y("value:Q"), color=alt.Color("param:N"), detail="type:N",
                tooltip=["date:T","param:N","type:N",alt.Tooltip("value:Q",format=".2f")],
            )
            styled = line.encode(strokeDash=alt.condition(alt.datum.type=='forecast', alt.value([5,5]), alt.value([0])))
            st.altair_chart(styled, use_container_width=True)
