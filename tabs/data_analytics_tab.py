# tabs/data_analytics_tab.py (Final Version with Interactive Dashboard)
"""
tabs/data_analytics_tab.py – multi-tank aware 🎛️

Provides a customizable **Data & Analytics** view with visualisation controls,
raw-data layout, rolling averages, correlation matrix, scatter/regression,
and basic forecasting. All queries are scoped to the **selected tank**.
"""

import datetime
from typing import List, Optional, Tuple, Dict, Callable

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from aqualog_db.repositories import TankRepository, WaterTestRepository
from aqualog_db.connection import get_connection
from utils import is_mobile, clean_numeric_df, translate
from config import SAFE_RANGES

# ======================================================================================
# MODULAR RENDER FUNCTIONS FOR EACH PANEL
# ======================================================================================

def render_interactive_dashboard(vis_df: pd.DataFrame):
    """
    Renders an interactive dashboard with cross-filtering.
    """
    with st.expander("🔬 Interactive Cross-Filtering Dashboard", expanded=True):
        if vis_df.empty or vis_df.shape[0] < 2:
            st.info("Not enough data to create an interactive dashboard.")
            return

        # 1. Create an interval selection brush
        brush = alt.selection_interval(encodings=['x'], name="date_brush")

        # 2. Create the main time-series chart
        base_chart = alt.Chart(vis_df).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip('parameter:N'),
                alt.Tooltip('value:Q', format='.2f')
            ]
        ).transform_fold(
            ['ph', 'ammonia', 'nitrite', 'nitrate'],
            as_=['parameter', 'value']
        ).properties(
            title="Parameter Trends (Drag on chart to select a date range)",
            height=300
        )

        main_chart_with_brush = base_chart.encode(
            color=alt.condition(brush, 'parameter:N', alt.value('lightgray'), title="Parameter")
        ).add_selection(
            brush
        )
        
        # 3. Create the detail chart (Scatter Plot)
        scatter_plot = alt.Chart(vis_df).mark_circle(size=80).encode(
            x=alt.X('kh:Q', title='KH (°dKH)'),
            y=alt.Y('gh:Q', title='GH (°dGH)'),
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip('kh:Q'),
                alt.Tooltip('gh:Q')
            ]
        ).properties(
            title="KH vs. GH (Updates based on selected date range)"
        ).transform_filter(
            brush
        )

        # 4. Combine and display the charts
        dashboard = main_chart_with_brush & scatter_plot

        st.altair_chart(dashboard, use_container_width=True)

def render_raw_data_table(vis_df: pd.DataFrame, tank_name: str, start_date: datetime.date, end_date: datetime.date):
    """Renders the raw data table and download button."""
    with st.expander("🗂️ Raw Data Table", expanded=False):
        st.dataframe(vis_df, use_container_width=True)
        csv_bytes = vis_df.to_csv(index=False).encode()
        st.download_button(
            "📥 Download Filtered Data as CSV",
            csv_bytes,
            file_name=f"aqualog_data_{tank_name}_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )

def render_rolling_averages(vis_df: pd.DataFrame, numeric_params: List[str]):
    """Renders the 30-day rolling averages chart."""
    with st.expander("🔄 30-Day Rolling Averages", expanded=False):
        df_idx = vis_df.set_index("date")
        all_roll = []
        for param in numeric_params:
            roll_ser = df_idx[param].rolling("30D", min_periods=1).mean().reset_index().rename(columns={param: "value"})
            roll_ser["param"] = param
            all_roll.append(roll_ser)
        
        if all_roll:
            combined = pd.concat(all_roll, ignore_index=True)
            chart = alt.Chart(combined).mark_line().encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("value:Q", title="30-Day Avg"),
                color=alt.Color("param:N", title="Parameter"),
                tooltip=["date:T", "param:N", alt.Tooltip("value:Q", format=".2f")],
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

def render_correlation_matrix(vis_df: pd.DataFrame, numeric_params: List[str]):
    """Renders the parameter correlation matrix."""
    with st.expander("🔗 Correlation Matrix", expanded=False):
        try:
            corr = vis_df[numeric_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception:
            st.error("Unable to compute correlation matrix.")

def render_scatter_regression(vis_df: pd.DataFrame, numeric_params: List[str]):
    """Renders the scatter plot with a regression line."""
    with st.expander("🔍 Scatter & Regression", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            xcol = st.selectbox("X-axis", numeric_params, index=0, key="scatter_x")
        with col2:
            ycol = st.selectbox("Y-axis", numeric_params, index=1 if len(numeric_params) > 1 else 0, key="scatter_y")
        
        df_sc = vis_df.dropna(subset=[xcol, ycol])
        if not df_sc.empty:
            scatter = alt.Chart(df_sc).mark_circle(size=60).encode(
                x=alt.X(f"{xcol}:Q", title=xcol.capitalize()),
                y=alt.Y(f"{ycol}:Q", title=ycol.capitalize()),
                tooltip=["date", xcol, ycol],
            )
            reg = scatter.transform_regression(xcol, ycol).mark_line(color="red")
            st.altair_chart(scatter + reg, use_container_width=True)
        else:
            st.write("Not enough data for scatter/regression.")

def render_forecast(vis_df: pd.DataFrame, numeric_params: List[str]):
    """Renders the 7-day forecast chart."""
    with st.expander("📈 7-Day Forecast", expanded=False):
        forecast_opts = ["All"] + numeric_params
        params_to_forecast = st.multiselect(
            "Forecast parameter(s)", options=forecast_opts, default=["All"], key="forecast_params"
        )

        if "All" in params_to_forecast or not params_to_forecast:
            params_to_plot = numeric_params
        else:
            params_to_plot = params_to_forecast

        all_plot_dfs = []
        for param in params_to_plot:
            series = vis_df.set_index("date")[param].dropna()
            if len(series) < 2: continue
            try:
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                forecast = model.forecast(7)
                last_date = series.index.max()
                fut_dates = pd.date_range(last_date + datetime.timedelta(days=1), periods=7, freq="D")
                fc_df = pd.DataFrame({"date": fut_dates, "value": forecast.values, "type": "forecast", "param": param})
                hist_df = series.reset_index().rename(columns={param: "value"})
                hist_df["type"] = "historical"
                hist_df["param"] = param
                all_plot_dfs.extend([hist_df, fc_df])
            except Exception:
                st.warning(f"Could not generate forecast for '{param}'.")
        
        if all_plot_dfs:
            plot_df = pd.concat(all_plot_dfs, ignore_index=True)
            line = alt.Chart(plot_df).mark_line().encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("value:Q", title="Value"),
                color=alt.Color("param:N", title="Parameter"),
                detail='type:N',
                tooltip=["date", "param:N", "type:N", alt.Tooltip("value:Q", format=".2f")],
            ).properties(height=300)
            styled_line = line.encode(strokeDash=alt.condition(alt.datum.type == 'forecast', alt.value([5, 5]), alt.value([0])))
            st.altair_chart(styled_line, use_container_width=True)
        else:
            st.info("Select one or more parameters with sufficient data to generate a forecast.")


def _get_min_max_dates(cur, tank_id: int) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    """Helper to get the min/max dates for a given tank."""
    cur.execute("SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;", (tank_id,))
    row = cur.fetchone()
    def _parse(val: str | None) -> Optional[datetime.date]:
        if not val: return None
        try: return datetime.datetime.fromisoformat(val).date()
        except Exception:
            try: return pd.to_datetime(val, errors="coerce").date()
            except Exception: return None
    if not row or not row[0]: return None, None
    return _parse(row[0]), _parse(row[1])

# ======================================================================================
# MAIN TAB FUNCTION
# ======================================================================================

def data_analytics_tab() -> None:
    """Render the Data & Analytics tab scoped to the active tank."""
    
    # --- Data Loading and Prep ---
    tank_id: int = st.session_state.get("tank_id", 1)
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

    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range(
        datetime.datetime.combine(min_date, datetime.time.min).isoformat(),
        datetime.datetime.combine(max_date, datetime.time.max).isoformat(),
        tank_id
    )
    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name}.")
        return
        
    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    
    numeric_params = df_clean.select_dtypes(include=np.number).columns.tolist()
    numeric_params = [p for p in numeric_params if p not in ['id', 'tank_id']]

    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name}.")
        return

    # --- Widget Definition ---
    WIDGETS: Dict[str, Tuple[str, Callable]] = {
        "interactive": ("🔬 Interactive Dashboard", render_interactive_dashboard),
        "raw_data": ("🗂️ Raw Data Table", render_raw_data_table),
        "rolling_avg": ("🔄 30-Day Rolling Averages", render_rolling_averages),
        "correlation": ("🔗 Correlation Matrix", render_correlation_matrix),
        "scatter": ("🔍 Scatter & Regression", render_scatter_regression),
        "forecast": ("📈 7-Day Forecast", render_forecast),
    }
    
    # --- UI Rendering ---
    with st.expander("🔧 Visualisation Controls", expanded=True):
        st.date_input(
            translate("Select Date Range"), value=[min_date, max_date],
            min_value=min_date, max_value=max_date, key="vis_date_range"
        )
    
    # Filter dataframe based on date controls
    start_date, end_date = st.session_state.vis_date_range
    vis_df = df_clean[(df_clean["date"].dt.date >= start_date) & (df_clean["date"].dt.date <= end_date)]

    # Default to all panels if none are selected in session state
    if 'dashboard_panels' not in st.session_state:
        st.session_state.dashboard_panels = list(WIDGETS.keys())

    # ADD THE NEW INTERACTIVE DASHBOARD
    render_interactive_dashboard(vis_df)

    # Loop through the user's selections (set in the sidebar) and render the other panels
    for panel_key in st.session_state.dashboard_panels:
        if panel_key in WIDGETS and panel_key != "interactive":
            _label, render_func = WIDGETS[panel_key]
            if panel_key == 'raw_data':
                render_func(vis_df, tank_name, start_date, end_date)
            else:
                render_func(vis_df, numeric_params)