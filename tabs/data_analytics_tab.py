# tabs/data_analytics_tab.py
"""
tabs/data_analytics_tab.py – multi-tank aware 🎛️

Provides a customizable **Data & Analytics** view with visualisation controls,
raw-data layout, rolling averages, correlation matrix, scatter/regression,
and basic forecasting. All queries are scoped to the **selected tank**,
offering deep insights into water quality trends and relationships.
"""

import datetime
from typing import List, Optional, Tuple, Dict, Callable
import sqlite3
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
# These functions are responsible for rendering individual sections of the analytics tab.
# ======================================================================================

def render_interactive_dashboard(vis_df: pd.DataFrame):
    """
    Renders an interactive dashboard with cross-filtering capabilities using Altair.

    This dashboard includes a main time-series chart and a detail scatter plot
    that updates based on the date range selected on the main chart.

    Args:
        vis_df: The DataFrame containing the water test data for visualisation.
                Expected to have a 'date' column and numeric parameter columns.
    """
    with st.expander("🔬 Interactive Cross-Filtering Dashboard", expanded=True):
        if vis_df.empty or vis_df.shape[0] < 2:
            st.info("Not enough data to create an interactive dashboard. Please log more water tests.")
            return

        # 1. Create an interval selection brush for date range filtering.
        brush = alt.selection_interval(encodings=['x'], name="date_brush")

        # 2. Create the main time-series chart.
        # It folds multiple parameter columns into 'parameter' and 'value' for charting.
        base_chart = alt.Chart(vis_df).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip('parameter:N'),
                alt.Tooltip('value:Q', format='.2f')
            ]
        ).transform_fold(
            ['ph', 'ammonia', 'nitrite', 'nitrate'], # Parameters to plot on the main chart
            as_=['parameter', 'value']
        ).properties(
            title="Parameter Trends (Drag on chart to select a date range)",
            height=300
        )

        # Apply the brush selection to the main chart, making non-selected areas light gray.
        main_chart_with_brush = base_chart.encode(
            color=alt.condition(brush, 'parameter:N', alt.value('lightgray'), title="Parameter")
        ).add_selection(
            brush # Add the interactive brush to this chart
        )
        
        # 3. Create the detail chart (Scatter Plot).
        # This chart is filtered by the date range selected on the main chart.
        scatter_plot = alt.Chart(vis_df).mark_circle(size=80).encode(
            x=alt.X('kh:Q', title='KH (°dKH)'), # Example: KH on X-axis
            y=alt.Y('gh:Q', title='GH (°dGH)'), # Example: GH on Y-axis
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip('kh:Q', format=".1f"), # Format tooltip values
                alt.Tooltip('gh:Q', format=".1f")
            ]
        ).properties(
            title="KH vs. GH (Updates based on selected date range)"
        ).transform_filter(
            brush # Filter this scatter plot based on the brush selection
        )

        # 4. Combine and display the charts vertically.
        dashboard = main_chart_with_brush & scatter_plot

        st.altair_chart(dashboard, use_container_width=True)

def render_raw_data_table(vis_df: pd.DataFrame, tank_name: str, start_date: datetime.date, end_date: datetime.date):
    """
    Renders the raw data table for the selected date range and provides a download button.

    Args:
        vis_df: The DataFrame containing the water test data to display.
        tank_name: The name of the current tank.
        start_date: The start date of the displayed data.
        end_date: The end date of the displayed data.
    """
    with st.expander("🗂️ Raw Data Table", expanded=False):
        st.dataframe(vis_df, use_container_width=True)
        
        # Prepare CSV data for download.
        csv_bytes = vis_df.to_csv(index=False).encode()
        st.download_button(
            "📥 Download Filtered Data as CSV",
            csv_bytes,
            file_name=f"aqualog_data_{tank_name}_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )

def render_rolling_averages(vis_df: pd.DataFrame, numeric_params: List[str]):
    """
    Renders a line chart showing 30-day rolling averages for selected numeric parameters.

    Args:
        vis_df: The DataFrame containing the water test data.
        numeric_params: A list of column names (parameters) that are numeric.
    """
    with st.expander("🔄 30-Day Rolling Averages", expanded=False):
        if vis_df.empty or vis_df.shape[0] < 30: # Need sufficient data for rolling average
            st.info("Not enough data points (at least 30 recommended) for rolling averages.")
            return

        df_idx = vis_df.set_index("date") # Set 'date' as index for rolling window
        all_roll = []
        for param in numeric_params:
            # Calculate rolling mean for each parameter
            roll_ser = df_idx[param].rolling("30D", min_periods=1).mean().reset_index().rename(columns={param: "value"})
            roll_ser["param"] = param # Add parameter name as a column for Altair
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
        else:
            st.info("No numeric parameters with sufficient data to compute rolling averages.")

def render_correlation_matrix(vis_df: pd.DataFrame, numeric_params: List[str]):
    """
    Renders a correlation matrix for selected numeric parameters.

    Args:
        vis_df: The DataFrame containing the water test data.
        numeric_params: A list of column names (parameters) that are numeric.
    """
    with st.expander("🔗 Correlation Matrix", expanded=False):
        if len(numeric_params) < 2:
            st.info("Need at least two numeric parameters to compute a correlation matrix.")
            return
        try:
            # Calculate pairwise correlation for numeric columns
            corr = vis_df[numeric_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception:
            st.error("Unable to compute correlation matrix. Ensure there is enough variance in the data.")

def render_scatter_regression(vis_df: pd.DataFrame, numeric_params: List[str]):
    """
    Renders a scatter plot with an optional regression line between two selected parameters.

    Args:
        vis_df: The DataFrame containing the water test data.
        numeric_params: A list of column names (parameters) that are numeric.
    """
    with st.expander("🔍 Scatter & Regression", expanded=False):
        if len(numeric_params) < 2:
            st.info("Need at least two numeric parameters for scatter plot and regression.")
            return

        col1, col2 = st.columns(2)
        with col1:
            # Select parameter for X-axis
            xcol = st.selectbox("X-axis", numeric_params, index=0, key="scatter_x")
        with col2:
            # Select parameter for Y-axis, defaulting to the second parameter if available
            ycol = st.selectbox("Y-axis", numeric_params, index=1 if len(numeric_params) > 1 else 0, key="scatter_y")
        
        # Drop rows with NaN in selected columns for accurate plotting
        df_sc = vis_df.dropna(subset=[xcol, ycol])
        
        if not df_sc.empty:
            scatter = alt.Chart(df_sc).mark_circle(size=60).encode(
                x=alt.X(f"{xcol}:Q", title=xcol.capitalize()),
                y=alt.Y(f"{ycol}:Q", title=ycol.capitalize()),
                tooltip=["date", xcol, ycol],
            )
            # Add a linear regression line to the scatter plot
            reg = scatter.transform_regression(xcol, ycol).mark_line(color="red")
            st.altair_chart(scatter + reg, use_container_width=True)
        else:
            st.write("Not enough data for scatter/regression plot after dropping missing values.")

def render_forecast(vis_df: pd.DataFrame, numeric_params: List[str]):
    """
    Renders a 7-day forecast for selected water parameters using Exponential Smoothing.

    Args:
        vis_df: The DataFrame containing historical water test data.
        numeric_params: A list of column names (parameters) that are numeric.
    """
    with st.expander("📈 7-Day Forecast", expanded=False):
        if vis_df.empty or vis_df.shape[0] < 2: # At least two data points for forecasting
            st.info("Not enough data to generate a forecast. Please log more water tests.")
            return

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
            # Create a time series from the parameter data, indexed by date, dropping NaNs
            series = vis_df.set_index("date")[param].dropna()
            
            if len(series) < 2: # Need at least 2 points to build a simple time series model
                st.warning(f"Not enough data points to generate forecast for '{param}'. (Min 2 required)")
                continue
            
            try:
                # Use ExponentialSmoothing model for forecasting
                # 'add' trend is suitable for data with linear trends
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                forecast = model.forecast(7) # Forecast 7 steps into the future
                
                # Create future dates for the forecast
                last_date = series.index.max()
                fut_dates = pd.date_range(last_date + datetime.timedelta(days=1), periods=7, freq="D")
                
                # Prepare forecast DataFrame
                fc_df = pd.DataFrame({"date": fut_dates, "value": forecast.values, "type": "forecast", "param": param})
                
                # Prepare historical data DataFrame for plotting
                hist_df = series.reset_index().rename(columns={param: "value"})
                hist_df["type"] = "historical"
                hist_df["param"] = param
                
                all_plot_dfs.extend([hist_df, fc_df])
            except Exception as e:
                st.warning(f"Could not generate forecast for '{param}'. Error: {e}")
        
        if all_plot_dfs:
            plot_df = pd.concat(all_plot_dfs, ignore_index=True)
            
            # Create Altair line chart
            line = alt.Chart(plot_df).mark_line().encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("value:Q", title="Value"),
                color=alt.Color("param:N", title="Parameter"),
                detail='type:N', # Use 'type' for differentiation (historical vs. forecast)
                tooltip=["date", "param:N", "type:N", alt.Tooltip("value:Q", format=".2f")],
            ).properties(height=300)
            
            # Style the forecast line differently (e.g., dashed)
            styled_line = line.encode(strokeDash=alt.condition(alt.datum.type == 'forecast', alt.value([5, 5]), alt.value([0])))
            st.altair_chart(styled_line, use_container_width=True)
        else:
            st.info("Select one or more parameters with sufficient data to generate a forecast.")


def _get_min_max_dates(cur: sqlite3.Cursor, tank_id: int) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    """
    Helper function to get the minimum and maximum dates of water test data
    for a given tank from the database.

    Args:
        cur: An active SQLite database cursor.
        tank_id: The ID of the tank.

    Returns:
        A tuple containing the minimum and maximum dates as datetime.date objects,
        or (None, None) if no data is found for the tank.
    """
    cur.execute("SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;", (tank_id,))
    row = cur.fetchone()

    def _parse(val: str | None) -> Optional[datetime.date]:
        """Internal helper to parse date strings robustly."""
        if not val: return None
        try: return datetime.datetime.fromisoformat(val).date()
        except Exception:
            try: return pd.to_datetime(val, errors="coerce").date()
            except Exception: return None

    if not row or not row[0]: return None, None # No data found
    return _parse(row[0]), _parse(row[1])

# ======================================================================================
# MAIN TAB FUNCTION
# ======================================================================================

def data_analytics_tab() -> None:
    """
    Renders the main "Data & Analytics" tab for the AquaLog application.

    This tab provides various tools for analyzing water test data, including
    an interactive dashboard, raw data table, rolling averages, correlation matrix,
    scatter plots with regression, and a 7-day forecast. All data displayed
    is scoped to the currently selected tank.
    """
    
    # --- Data Loading and Preparation ---
    tank_id: int = st.session_state.get("tank_id", 1) # Get current tank ID
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")
    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    # Fetch min/max dates for the selected tank to set date picker bounds
    with get_connection() as conn:
        cur = conn.cursor()
        min_date, max_date = _get_min_max_dates(cur, tank_id)
    
    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}. Please log water tests to see analytics.")
        return

    # Fetch all water test data for the selected tank
    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range(
        datetime.datetime.combine(min_date, datetime.time.min).isoformat(),
        datetime.datetime.combine(max_date, datetime.time.max).isoformat(),
        tank_id
    )
    
    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name} within the available date range.")
        return
        
    # Clean and preprocess data for numeric analysis
    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    
    # Identify numeric parameters available in the data for analysis
    numeric_params = df_clean.select_dtypes(include=np.number).columns.tolist()
    # Exclude internal ID columns from numeric parameters for analysis
    numeric_params = [p for p in numeric_params if p not in ['id', 'tank_id']]

    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name} to perform analytics.")
        return

    # --- Widget Definition Map ---
    # Maps internal keys to display labels and rendering functions for each panel.
    WIDGETS: Dict[str, Tuple[str, Callable]] = {
        "interactive": ("🔬 Interactive Dashboard", render_interactive_dashboard),
        "raw_data": ("🗂️ Raw Data Table", render_raw_data_table),
        "rolling_avg": ("🔄 30-Day Rolling Averages", render_rolling_averages),
        "correlation": ("🔗 Correlation Matrix", render_correlation_matrix),
        "scatter": ("🔍 Scatter & Regression", render_scatter_regression),
        "forecast": ("📈 7-Day Forecast", render_forecast),
    }
    
    # --- UI Rendering Controls ---
    with st.expander("🔧 Visualisation Controls", expanded=True):
        # Date range selector for filtering the data displayed in the panels
        selected_date_range = st.date_input(
            translate("Select Date Range"), value=[min_date, max_date],
            min_value=min_date, max_value=max_date, key="vis_date_range"
        )
    
    # Ensure selected_date_range is a tuple of two dates
    if isinstance(selected_date_range, list) and len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
    else:
        # Fallback if the date input returns a single date or None
        start_date = min_date
        end_date = max_date

    # Filter dataframe based on date controls selected by the user
    vis_df = df_clean[(df_clean["date"].dt.date >= start_date) & (df_clean["date"].dt.date <= end_date)]

    # Initialize dashboard_panels in session state if not already present
    # This prevents an error if the user hasn't interacted with the multiselect yet.
    if 'dashboard_panels' not in st.session_state:
        st.session_state.dashboard_panels = list(WIDGETS.keys()) # Default to all panels

    # Always render the new interactive dashboard first (it's the primary view now)
    render_interactive_dashboard(vis_df)

    # Loop through the user's selections and render the other panels
    # Skip 'interactive' as it's already rendered
    for panel_key in st.session_state.dashboard_panels:
        if panel_key in WIDGETS and panel_key != "interactive":
            _label, render_func = WIDGETS[panel_key]
            # Pass specific arguments based on the panel type
            if panel_key == 'raw_data':
                render_func(vis_df, tank_name, start_date, end_date)
            else:
                render_func(vis_df, numeric_params)