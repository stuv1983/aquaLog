# tabs/data_analytics_tab.py (Corrected)
"""
tabs/data_analytics_tab.py – multi-tank aware 🎛️

Provides the **Data & Analytics** view with visualisation controls, raw-data
layout, rolling averages, correlation matrix, scatter/regression, basic
forecasting, and full CSV export. All queries are scoped to the **selected tank**.
"""

import datetime
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from aqualog_db.repositories import TankRepository, WaterTestRepository
from aqualog_db.connection import get_connection

from utils import (
    is_mobile,
    clean_numeric_df,
    translate,
)
from config import SAFE_RANGES


def _get_min_max_dates(cur, tank_id: int) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    """Helper to get the min/max dates for a given tank."""
    cur.execute(
        "SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;",
        (tank_id,),
    )
    row = cur.fetchone()
    def _parse(val: Optional[str]) -> Optional[datetime.date]:
        if not val:
            return None
        try:
            return datetime.datetime.fromisoformat(val).date()
        except Exception:
            pd_ts = pd.to_datetime(val, errors="coerce")
            return pd_ts.date() if not pd.isna(pd_ts) else None
    if not row or not row[0]:
        return None, None
    return _parse(row[0]), _parse(row[1])


def data_analytics_tab() -> None:
    """Render the Data & Analytics tab scoped to the active tank."""
    tank_id: int = st.session_state.get("tank_id", 1)
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")
    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    # Fetch raw data
    with get_connection() as conn:
        cur = conn.cursor()
        min_date, max_date = _get_min_max_dates(cur, tank_id)

    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}.")
        return

    start_str = datetime.datetime.combine(min_date, datetime.time.min).isoformat()
    end_str = datetime.datetime.combine(max_date, datetime.time.max).isoformat()
    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range(start_str, end_str, tank_id)

    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name}.")
        return

    # Clean and coerce numeric fields
    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    # Identify numeric parameters (exclude id fields)
    candidate_cols = df_clean.columns.difference(["id", "tank_id", "date"])
    # Coerce all candidate columns to numeric to avoid string vs float comparisons
    for col in candidate_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    # After coercion, drop rows where all candidate cols are NaN
    df_clean = df_clean.dropna(subset=candidate_cols, how='all')
    numeric_params = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df_clean[c])]

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
            sd, ed = date_range
            if sd > ed:
                st.error(translate("Start date must be on or before end date."))
                return
            vis_df = df_clean[(df_clean["date"].dt.date >= sd) & (df_clean["date"].dt.date <= ed)]
        else:
            vis_df = df_clean

    # --- Raw Data Table & CSV Export ---
    with st.expander("🗂️ Raw Data Table", expanded=False):
        st.dataframe(vis_df, use_container_width=True)
        csv_bytes = vis_df.to_csv(index=False).encode()
        st.download_button(
            "📥 Download Filtered Data as CSV",
            csv_bytes,
            file_name=f"aqualog_{tank_name}_{min_date}_to_{max_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # --- 30-Day Rolling Averages ---
    with st.expander("🔄 30-Day Rolling Averages", expanded=False):
        df_idx = vis_df.set_index("date")
        all_roll = []
        for param in numeric_params:
            ser = df_idx[param]
            # Skip if no valid numeric data
            if ser.dropna().empty:
                continue
            roll_ser = (
                ser.rolling("30D", min_periods=1)
                   .mean()
                   .reset_index()
                   .rename(columns={param: "value"})
            )
            roll_ser["param"] = param
            all_roll.append(roll_ser)
        if all_roll:
            combined = pd.concat(all_roll, ignore_index=True)
            chart = (
                alt.Chart(combined).mark_line().encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("value:Q", title="30-Day Avg"),
                    color=alt.Color("param:N", title="Parameter"),
                    tooltip=["date:T", "param:N", alt.Tooltip("value:Q", format=".2f")],
                ).properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

    # --- Correlation Matrix ---
    with st.expander("🔗 Correlation Matrix", expanded=False):
        try:
            corr = vis_df[numeric_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception:
            st.error(translate("Unable to compute correlation matrix."))

    # --- Scatter & Regression ---
    with st.expander("🔍 Scatter & Regression", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            xcol = st.selectbox("X-axis", numeric_params, index=0, key="scatter_x")
        with col2:
            ycol = st.selectbox("Y-axis", numeric_params, index=1 if len(numeric_params) > 1 else 0, key="scatter_y")
        df_sc = vis_df.dropna(subset=[xcol, ycol])
        if not df_sc.empty:
            scatter = (
                alt.Chart(df_sc).mark_circle(size=60).encode(
                    x=alt.X(f"{xcol}:Q", title=xcol.capitalize()),
                    y=alt.Y(f"{ycol}:Q", title=ycol.capitalize()),
                    tooltip=["date", xcol, ycol],
                )
            )
            reg_line = scatter.transform_regression(xcol, ycol).mark_line(color="red")
            st.altair_chart(scatter + reg_line, use_container_width=True)
        else:
            st.info(translate("Not enough data for scatter/regression."))

    # --- 7-Day Forecast ---
    with st.expander("📈 7-Day Forecast", expanded=False):
        forecast_opts = ["All"] + numeric_params
        params_to_forecast = st.multiselect(
            translate("Forecast parameter(s)"),
            options=forecast_opts,
            default=["All"],
            key="forecast_params"
        )
        if "All" in params_to_forecast or not params_to_forecast:
            to_plot = numeric_params
        else:
            to_plot = params_to_forecast

        all_plot_dfs = []
        for param in to_plot:
            series = vis_df.set_index("date")[param].dropna()
            if len(series) < 2:
                continue
            try:
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                forecast = model.forecast(7)
                last_date = series.index.max()
                fut_dates = pd.date_range(last_date + datetime.timedelta(days=1), periods=7, freq="D")
                fc_df = pd.DataFrame({"date": fut_dates, "value": forecast.values, "type": "forecast"})
                hist_df = series.reset_index().rename(columns={param: "value"})
                hist_df["type"] = "historical"
                fc_df["param"] = param
                hist_df["param"] = param
                all_plot_dfs.extend([hist_df, fc_df])
            except Exception:
                st.warning(f"Could not generate forecast for '{param}'.")
        if all_plot_dfs:
            plot_df = pd.concat(all_plot_dfs, ignore_index=True)
            line = (
                alt.Chart(plot_df).mark_line().encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("value:Q", title="Value"),
                    color=alt.Color("param:N", title="Parameter"),
                    detail='type:N',
                    tooltip=["date", "param:N", "type:N", alt.Tooltip("value:Q", format=".2f")],
                ).properties(height=300)
            )
            styled_line = line.encode(
                strokeDash=alt.condition(alt.datum.type == 'forecast', alt.value([5, 5]), alt.value([0]))
            )
            st.altair_chart(styled_line, use_container_width=True)
        else:
            st.info(translate("Select one or more parameters with sufficient data to generate a forecast."))
