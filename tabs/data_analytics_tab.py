"""
tabs/data_analytics_tab.py – multi-tank aware 🎛️
Provides the **Data & Analytics** view with visualisation controls, raw-data
layout, rolling averages, correlation matrix, scatter/regression, basic
forecasting, and full CSV export. All queries are scoped to the **selected tank**
via `st.session_state["tank_id"]` (fallback = 1).

Updated: 2025-06-15 (fixed get_connection usage)
"""

import datetime
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st
import altair as alt

# ——— Refactored DB imports ———
from aqualog_db.legacy import fetch_data, fetch_all_tanks
from aqualog_db.base import BaseRepository
from aqualog_db.connection import get_connection

from utils import (
    is_mobile,
    clean_numeric_df,
    translate,
    format_with_units,
    is_out_of_range,
)
from config import SAFE_RANGES

print(">>> LOADING", __file__)

def _get_min_max_dates(cur, tank_id: int) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    cur.execute(
        "SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;",
        (tank_id,),
    )
    row = cur.fetchone()
    def _parse(val: str | None) -> Optional[datetime.date]:
        if not val:
            return None
        try:
            return datetime.datetime.fromisoformat(val).date()
        except Exception:
            try:
                pd_ts = pd.to_datetime(val, errors="coerce")
                return pd_ts.date() if not pd.isna(pd_ts) else None
            except Exception:
                return None
    if not row or not row[0]:
        return None, None
    return _parse(row[0]), _parse(row[1])


def data_analytics_tab() -> None:
    """Render the Data & Analytics tab scoped to the active tank."""
    tank_id: int = st.session_state.get("tank_id", 1)
    tanks = fetch_all_tanks()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")

    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    # 1️⃣ Get date range
    with get_connection() as conn:
        cur = conn.cursor()
        min_date, max_date = _get_min_max_dates(cur, tank_id)

    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}.")
        return

    # 2️⃣ Fetch data
    df = fetch_data(min_date.isoformat(), max_date.isoformat(), tank_id)
    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name}.")
        return

    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    numeric_params: List[str] = [c for c in df_clean.columns if c not in ("date", "notes", "id", "tank_id")]
    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name}.")
        return

    # 3️⃣ Visualisation controls
    st.markdown("### 🔧 " + translate("Visualisation Controls"))
    with st.expander(translate("Customise Chart"), expanded=not is_mobile()):
        date_range = st.date_input(
            translate("Select Date Range"),
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="vis_date_range",
        )
        start_date, end_date = date_range
        if start_date > end_date:
            st.error(translate("Start date must be on or before end date."))
            return

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

        chart_type = st.selectbox(
            translate("Chart Type"),
            [
                translate("Line Chart"),
                translate("Bar Chart"),
                translate("Scatter Plot"),
                translate("Rolling Avg (30d)")
            ],
            index=0,
            key="vis_chart_type",
        )

    vis_df = df_clean[
        (df_clean["date"] >= pd.to_datetime(start_date)) &
        (df_clean["date"] <= pd.to_datetime(end_date))
    ]

    # — existing summary & chart code unchanged —

    # — Full Data Table & CSV —
    with st.expander("🗂️ " + translate("Full Data"), expanded=False):
        st.markdown("#### " + translate("Raw Data Table") + " & Download")
        with get_connection() as conn_full:
            full_raw = pd.read_sql_query(
                "SELECT date, ph, ammonia, nitrite, nitrate, kh, gh, co2_indicator, temperature, notes "
                "FROM water_tests WHERE tank_id = ? ORDER BY date;",
                conn_full,
                params=(tank_id,)
            )
        full_clean = full_raw.copy()
        full_clean["date"] = pd.to_datetime(full_clean["date"], errors="coerce")
        numeric_cols = ["ph", "ammonia", "nitrite", "nitrate", "kh", "gh", "temperature"]
        for col in numeric_cols:
            full_clean[col] = pd.to_numeric(full_clean[col], errors="coerce")
        full_csv = full_clean.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 " + translate("Download Full Data (CSV)"),
            data=full_csv,
            file_name=f"water_tests_full_{tank_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        display_cols = [c for c in full_clean.columns if c != "notes"]
        table_df = full_clean[display_cols].copy()
        for col in numeric_cols:
            table_df[col] = table_df[col].apply(lambda v: f"{v:.2f}" if pd.notnull(v) else "N/A")
        renames = {
            'date': 'Date',
            'ph': 'pH',
            'ammonia': 'Ammonia (ppm)',
            'nitrite': 'Nitrite (ppm)',
            'nitrate': 'Nitrate (ppm)',
            'kh': 'KH (dKH)',
            'gh': 'GH (°dH)',
            'co2_indicator': 'CO₂ Indicator',
            'temperature': 'Temperature (°C)',
            'notes': 'Notes'
        }
        table_df.rename(columns=renames, inplace=True)
        st.dataframe(table_df, use_container_width=True)

    # -- Rolling Averages
    with st.expander("🔄 " + translate("30-Day Rolling Averages"), expanded=False):
        sel_roll = st.multiselect(
            translate("Select parameter(s)"),
            options=["All"] + numeric_params,
            default=["All"],
            key="roll_params"
        )
        roll_cols = numeric_params if "All" in sel_roll or not sel_roll else [p for p in sel_roll if p in numeric_params]
        if roll_cols:
            df_idx = df_clean.set_index("date")
            rolls = []
            for p in roll_cols:
                tmp = df_idx[p].rolling("30D", min_periods=1).mean().reset_index()
                tmp["param"] = "GH (°dH)" if p == "gh" else translate(p.capitalize())
                tmp.rename(columns={p: "value"}, inplace=True)
                rolls.append(tmp)
            combined = pd.concat(rolls, ignore_index=True)
            chart = (
                alt.Chart(combined)
                .mark_line()
                .encode(
                    x="date:T",
                    y="value:Q",
                    color="param:N",
                    tooltip=["date:T", "param:N", alt.Tooltip("value:Q", format=".2f")],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info(translate("Select at least one parameter."))

    # -- Out-of-range Events
    with st.expander("🚨 " + translate("Out-of-range Events"), expanded=False):
        oor_counts = {}
        oor_pct = {}
        for param in params_to_plot:
            if param in SAFE_RANGES:
                lo, hi = SAFE_RANGES[param]
                vals = vis_df[param].dropna()
                count = ((vals < lo) | (vals > hi)).sum()
                pct = 100 * count / max(1, len(vals))
                oor_counts[param] = count
                oor_pct[param] = pct
        if oor_counts:
            summary_df = pd.DataFrame({
                "Parameter": ["GH (°dH)" if p == "gh" else translate(p.capitalize()) for p in oor_counts],
                "Out-of-range count": list(oor_counts.values()),
                "Percent (%)": [f"{v:.1f}%" for v in oor_pct.values()],
            })
            st.dataframe(summary_df, use_container_width=True)
            st.bar_chart(pd.Series(oor_counts))
        else:
            st.info(translate("No out-of-range events for selected parameters."))
    # -- Comparative Analysis
    with st.expander("🔍 " + translate("Compare Two Parameters"), expanded=False):
        if len(numeric_params) < 2:
            st.info(translate("Not enough parameters for comparison."))
        else:
            xcol = st.selectbox("X-axis", numeric_params, key="sc_x")
            ycol = st.selectbox("Y-axis", numeric_params, key="sc_y")
            df_sc = vis_df.dropna(subset=[xcol, ycol])
            if len(df_sc) > 1:
                scatter = alt.Chart(df_sc).mark_circle(size=60).encode(
                    x=f"{xcol}:Q",
                    y=f"{ycol}:Q",
                    tooltip=["date:T", xcol, ycol],
                )
                reg = scatter.transform_regression(xcol, ycol).mark_line(color="red")
                st.altair_chart(scatter + reg, use_container_width=True)
                try:
                    from scipy.stats import pearsonr
                    corr_val, _ = pearsonr(df_sc[xcol], df_sc[ycol])
                    st.success(f"Pearson r: {corr_val:.2f}")
                except Exception:
                    st.warning(translate("Unable to compute Pearson correlation."))
            else:
                st.info(translate("Not enough data for scatter/regression."))

    # -- Forecasting
    with st.expander("📈 " + translate("7-Day Forecast"), expanded=False):
        if numeric_params:
            fc_param = st.selectbox(translate("Forecast parameter"), numeric_params, key="fc_param")
            series = vis_df.set_index("date")[fc_param].dropna()
            if len(series) < 2:
                st.warning(translate("Not enough data to forecast."))
            else:
                try:
                    from statsmodels.tsa.holtwinters import ExponentialSmoothing

                    model = ExponentialSmoothing(series, trend="add").fit(optimized=True)
                    forecast = model.forecast(7)
                    last = series.index.max()
                    dates = pd.date_range(last + datetime.timedelta(days=1), periods=7)
                    df_fc = pd.DataFrame({"date": dates, "value": forecast.values, "type": "forecast"})
                    df_hist = series.reset_index().rename(columns={fc_param: "value"})
                    df_hist["type"] = "historical"
                    plot_df = pd.concat([df_hist, df_fc], ignore_index=True)
                    chart = (
                        alt.Chart(plot_df)
                        .mark_line()
                        .encode(
                            x="date:T",
                            y="value:Q",
                            color="type:N",
                            tooltip=["date:T", "type:N", alt.Tooltip("value:Q", format=".2f")],
                        )
                        .properties(height=300)
                    )
                    st.altair_chart(chart, use_container_width=True)
                except Exception:
                    st.error(translate("Forecasting failed—ensure statsmodels is installed."))


