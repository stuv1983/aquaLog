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
from utils import is_mobile, clean_numeric_df, translate, detect_anomalies
from config import SAFE_RANGES

# ======================================================================================
# MODULAR RENDER FUNCTIONS FOR EACH PANEL
# ======================================================================================

def render_interactive_dashboard(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders an interactive dashboard with cross-filtering capabilities using Altair.

    This dashboard includes a main time-series chart and a detail scatter plot
    that updates dynamically based on the date range selected on the main chart,
    allowing for drill-down analysis.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data for visualisation.
                               Expected to have a 'date' column (datetime) and other
                               numeric parameter columns.
        numeric_params (List[str]): A list of all available numeric parameter column names in `vis_df`.
    """
    with st.expander("🔬 Interactive Cross-Filtering Dashboard", expanded=True):
        if vis_df.empty or vis_df.shape[0] < 2:
            st.info("Not enough data to create an interactive dashboard. Please log more water tests.")
            return

        # --- Parameter Selection for Charts ---
        st.markdown("**Chart Parameters Selection:**")
        
        # Multiselect for main trend chart parameters
        default_main_chart_params = [p for p in ['ph', 'ammonia', 'nitrite', 'nitrate'] if p in numeric_params]
        main_chart_params = st.multiselect(
            "Select parameters for **Main Trend Chart**:",
            options=numeric_params,
            default=default_main_chart_params,
            key="interactive_main_chart_params"
        )

        if not main_chart_params:
            st.warning("Please select at least one parameter for the Main Trend Chart.")
            return

        # Selectboxes for scatter plot parameters
        col_x, col_y = st.columns(2)
        with col_x:
            scatter_x_param = st.selectbox(
                "Select X-axis for **Scatter Plot**:",
                options=numeric_params,
                index=numeric_params.index('kh') if 'kh' in numeric_params else (0 if numeric_params else 0), # Default to 'kh'
                key="interactive_scatter_x"
            )
        with col_y:
            scatter_y_param = st.selectbox(
                "Select Y-axis for **Scatter Plot**:",
                options=numeric_params,
                index=numeric_params.index('gh') if 'gh' in numeric_params else (1 if len(numeric_params) > 1 else 0), # Default to 'gh'
                key="interactive_scatter_y"
            )
        
        st.markdown("---") # Separator for visual clarity

        # 1. Create an interval selection brush for date range filtering.
        # This brush will control the date range visible in the scatter plot.
        brush = alt.selection_interval(encodings=['x'], name="date_brush")

        # 2. Create the main time-series chart.
        # It folds multiple parameter columns into 'parameter' and 'value' for charting,
        # enabling Altair to draw multiple lines with different colors.
        base_chart = alt.Chart(vis_df).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip('parameter:N'),
                alt.Tooltip('value:Q', format='.2f')
            ]
        ).transform_fold(
            main_chart_params, # Use selected parameters for the main chart
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
        # This chart is filtered dynamically by the date range selected on the main chart using the brush.
        scatter_plot = alt.Chart(vis_df).mark_circle(size=80).encode(
            x=alt.X(f'{scatter_x_param}:Q', title=scatter_x_param.capitalize()), # Use selected X parameter
            y=alt.Y(f'{scatter_y_param}:Q', title=scatter_y_param.capitalize()), # Use selected Y parameter
            tooltip=[
                alt.Tooltip('date:T'),
                alt.Tooltip(f'{scatter_x_param}:Q', format=".1f"), # Format tooltip values
                alt.Tooltip(f'{scatter_y_param}:Q', format=".1f")
            ]
        ).properties(
            title=f"{scatter_x_param.capitalize()} vs. {scatter_y_param.capitalize()} (Updates based on selected date range)"
        ).transform_filter(
            brush # Filter this scatter plot based on the brush selection
        )

        # 4. Combine and display the charts vertically.
        dashboard = main_chart_with_brush & scatter_plot

        st.altair_chart(dashboard, use_container_width=True)

def render_raw_data_table(vis_df: pd.DataFrame, tank_name: str, start_date: datetime.date, end_date: datetime.date) -> None:
    """
    Renders the raw data table for the selected date range and provides a download button.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data to display.
                               This DataFrame should already be filtered by the selected date range.
        tank_name (str): The name of the current tank, used for the CSV download filename.
        start_date (datetime.date): The start date of the displayed data.
        end_date (datetime.date): The end date of the displayed data.
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

def render_rolling_averages(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders a line chart showing 30-day rolling averages for selected numeric parameters.

    This helps in identifying longer-term trends by smoothing out short-term fluctuations.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data. Expected to
                               have a 'date' column (datetime) and numeric parameter columns.
        numeric_params (List[str]): A list of column names (parameters) that are numeric
                                    and available for rolling average calculation.
    """
    with st.expander("🔄 30-Day Rolling Averages", expanded=False):
        # Need sufficient data for a meaningful rolling average (at least 30 days for a 30D window)
        if vis_df.empty or vis_df.shape[0] < 30:
            st.info("Not enough data points (at least 30 recommended) for rolling averages.")
            return

        # Multiselect for rolling averages
        rolling_params = st.multiselect(
            "Select parameters for rolling averages:",
            options=numeric_params,
            default=[p for p in ['ph', 'ammonia', 'nitrite', 'nitrate'] if p in numeric_params],
            key="rolling_avg_params"
        )
        if not rolling_params:
            st.info("No parameters selected for rolling averages.")
            return

        df_idx = vis_df.set_index("date") # Set 'date' as index for rolling window
        all_roll = []
        for param in rolling_params: # Use selected rolling parameters
            # Calculate rolling mean for each parameter using a 30-day window.
            # `min_periods=1` allows calculation even if less than 30 days of data
            # are available at the beginning of the time series.
            roll_ser = df_idx[param].rolling("30D", min_periods=1).mean().reset_index().rename(columns={param: "value"})
            roll_ser["param"] = param # Add parameter name as a column for Altair to differentiate lines
            all_roll.append(roll_ser)
        
        if all_roll:
            # Concatenate all rolling average series into a single DataFrame for plotting.
            combined = pd.concat(all_roll, ignore_index=True)
            chart = alt.Chart(combined).mark_line().encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("value:Q", title="30-Day Avg"),
                color=alt.Color("param:N", title="Parameter"),
                tooltip=["date:T", "param:N", alt.Tooltip("value:Q", format=".2f")],
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No numeric parameters with sufficient data to compute rolling averages based on your selection.")

def render_correlation_matrix(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders a correlation matrix for selected numeric parameters.

    This matrix helps visualize the statistical relationship between different
    water parameters.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data.
                               Expected to have numeric parameter columns.
        numeric_params (List[str]): A list of column names (parameters) that are numeric.
    """
    with st.expander("🔗 Correlation Matrix", expanded=False):
        if len(numeric_params) < 2:
            st.info("Need at least two numeric parameters to compute a correlation matrix.")
            return

        # Multiselect for correlation matrix parameters
        corr_params = st.multiselect(
            "Select parameters for correlation matrix:",
            options=numeric_params,
            default=numeric_params[:4] if len(numeric_params) >= 4 else numeric_params,
            key="correlation_matrix_params"
        )
        if len(corr_params) < 2:
            st.info("Please select at least two parameters for the correlation matrix.")
            return

        try:
            # Calculate pairwise correlation for selected numeric columns.
            # Missing values are handled by pandas' default `pairwise` drop.
            corr = vis_df[corr_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception as e:
            # Error might occur if selected parameters have no variance or too many missing values.
            st.error(f"Unable to compute correlation matrix. Ensure there is enough variance in the data and no missing values for selected parameters. Error: {e}")

def render_scatter_regression(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders a scatter plot with an optional linear regression line between two selected parameters.

    This plot helps visualize the direct relationship between two parameters and
    identify potential linear trends.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data.
                               Expected to have a 'date' column and numeric parameter columns.
        numeric_params (List[str]): A list of column names (parameters) that are numeric.
    """
    with st.expander("🔍 Scatter & Regression", expanded=False):
        if len(numeric_params) < 2:
            st.info("Need at least two numeric parameters for scatter plot and regression.")
            return

        col1, col2 = st.columns(2)
        with col1:
            # Select parameter for X-axis
            xcol = st.selectbox(
                "X-axis",
                numeric_params,
                index=numeric_params.index('kh') if 'kh' in numeric_params else (0 if numeric_params else 0), # Default to 'kh'
                key="scatter_x"
            )
        with col2:
            # Select parameter for Y-axis, defaulting to the second parameter if available
            ycol = st.selectbox(
                "Y-axis",
                numeric_params,
                index=numeric_params.index('gh') if 'gh' in numeric_params else (1 if len(numeric_params) > 1 else 0), # Default to 'gh'
                key="scatter_y"
            )
        
        # Drop rows with NaN in selected columns for accurate plotting and regression.
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
            st.write("Not enough data for scatter/regression plot after dropping missing values for selected parameters.")

def render_forecast(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders a 7-day forecast for selected water parameters using Exponential Smoothing.

    This provides a basic projection of future parameter levels based on historical data.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing historical water test data.
                               Expected to have a 'date' column (datetime) and numeric parameter columns.
        numeric_params (List[str]): A list of column names (parameters) that are numeric.
    """
    with st.expander("📈 7-Day Forecast", expanded=False):
        # At least two data points are needed to build a time series model for forecasting.
        if vis_df.empty or vis_df.shape[0] < 2:
            st.info("Not enough data to generate a forecast. Please log more water tests.")
            return

        # Multiselect for forecast parameters
        params_to_forecast_options = numeric_params
        params_to_forecast = st.multiselect(
            "Forecast parameter(s)",
            options=params_to_forecast_options,
            default=[p for p in ['ph', 'nitrate'] if p in numeric_params], # Default to a few common parameters
            key="forecast_params"
        )

        if not params_to_forecast:
            st.info("Select one or more parameters with sufficient data to generate a forecast.")
            return

        all_plot_dfs = []
        for param in params_to_forecast:
            # Create a time series from the parameter data, indexed by date, dropping NaNs.
            series = vis_df.set_index("date")[param].dropna()
            
            if len(series) < 2: # Need at least 2 points to build a simple time series model
                st.warning(f"Not enough data points to generate forecast for '{param}'. (Min 2 required)")
                continue
            
            try:
                # Use ExponentialSmoothing model for forecasting.
                # 'add' trend is suitable for data with linear trends.
                # `seasonal=None` indicates no seasonal component.
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                forecast = model.forecast(7) # Forecast 7 steps into the future
                
                # Create future dates for the forecast, starting one day after the last historical date.
                last_date = series.index.max()
                fut_dates = pd.date_range(last_date + datetime.timedelta(days=1), periods=7, freq="D")
                
                # Prepare forecast DataFrame
                fc_df = pd.DataFrame({"date": fut_dates, "value": forecast.values, "type": "forecast", "param": param})
                
                # Prepare historical data DataFrame for plotting alongside the forecast.
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
            
            # Style the forecast line differently (e.g., dashed) to distinguish from historical data.
            styled_line = line.encode(strokeDash=alt.condition(alt.datum.type == 'forecast', alt.value([5, 5]), alt.value([0])))
            st.altair_chart(styled_line, use_container_width=True)
        else:
            st.info("No forecast can be displayed with current selections or data.")

def render_anomaly_detection(vis_df: pd.DataFrame, numeric_params: List[str]) -> None:
    """
    Renders an anomaly detection chart for selected water parameters.

    Args:
        vis_df (pd.DataFrame): The DataFrame containing the water test data.
        numeric_params (List[str]): A list of numeric parameter column names.
    """
    with st.expander("🚨 Anomaly Detection", expanded=False):
        if len(numeric_params) < 2:
            st.info("Need at least two numeric parameters to detect anomalies.")
            return

        anomaly_params = st.multiselect(
            "Select parameters for anomaly detection:",
            options=numeric_params,
            default=numeric_params[:4] if len(numeric_params) >= 4 else numeric_params,
            key="anomaly_detection_params"
        )

        if len(anomaly_params) < 2:
            st.info("Please select at least two parameters for anomaly detection.")
            return

        # Detect anomalies in the data
        df_with_anomalies = detect_anomalies(vis_df, anomaly_params)
        anomalies = df_with_anomalies[df_with_anomalies['anomaly'] == -1]

        # Create a chart to visualize the anomalies
        base_chart = alt.Chart(df_with_anomalies).mark_line(point=True).encode(
            x='date:T',
            y=alt.Y(alt.repeat("layer"), type='quantitative'),
            color=alt.Color(alt.repeat("layer"), type='nominal')
        ).repeat(
            layer=anomaly_params
        )

        anomaly_points = alt.Chart(anomalies).mark_circle(
            size=100,
            color='red'
        ).encode(
            x='date:T',
            y=alt.Y(alt.repeat("layer"), type='quantitative')
        ).repeat(
            layer=anomaly_params
        )

        st.altair_chart(base_chart + anomaly_points, use_container_width=True)

        if not anomalies.empty:
            st.write("Detected Anomalies:")
            st.dataframe(anomalies[['date'] + anomaly_params])
        else:
            st.success("No anomalies detected in the selected parameters.")


def _get_min_max_dates(cur: sqlite3.Cursor, tank_id: int) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    """
    Helper function to retrieve the minimum and maximum dates of water test data
    for a given tank from the database.

    Args:
        cur (sqlite3.Cursor): An active SQLite database cursor.
        tank_id (int): The ID of the tank to retrieve min/max dates for.

    Returns:
        tuple[Optional[datetime.date], Optional[datetime.date]]: A tuple containing
                                                                 the minimum and maximum dates
                                                                 as `datetime.date` objects.
                                                                 Returns `(None, None)` if no data
                                                                 is found for the specified tank.
    """
    cur.execute("SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;", (tank_id,))
    row = cur.fetchone()

    def _parse(val: str | None) -> Optional[datetime.date]:
        """Internal helper to parse date strings robustly to datetime.date objects."""
        if not val: return None
        try: return datetime.datetime.fromisoformat(val).date()
        except Exception: # Fallback for potentially malformed ISO strings (e.g., missing time part)
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
    is scoped to the currently selected tank, enhancing focused insights.
    """
    
    # --- Data Loading and Preparation ---
    # Get the current tank ID from Streamlit's session state.
    tank_id: int = st.session_state.get("tank_id", 1)
    # Fetch tank details to display the tank name.
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")
    st.header(f"📊 {translate('Data & Analytics')} — {tank_name}")

    # Fetch min/max dates for the selected tank to set dynamic date picker bounds.
    with get_connection() as conn:
        cur = conn.cursor()
        min_date, max_date = _get_min_max_dates(cur, tank_id)
    
    if min_date is None or max_date is None:
        st.info(translate("No data available for") + f" {tank_name}. Please log water tests to see analytics.")
        return

    # Fetch all water test data for the selected tank within the determined date range.
    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range(
        datetime.datetime.combine(min_date, datetime.time.min).isoformat(),
        datetime.datetime.combine(max_date, datetime.time.max).isoformat(),
        tank_id
    )
    
    if df.empty:
        st.info(translate("No data to display for") + f" {tank_name} within the available date range.")
        return
        
    # Clean and preprocess data for numeric analysis and consistent plotting.
    df_clean = clean_numeric_df(df).dropna(subset=["date"])
    
    # Identify numeric parameters available in the data for analysis, excluding internal IDs.
    numeric_params = df_clean.select_dtypes(include=np.number).columns.tolist()
    numeric_params = [p for p in numeric_params if p not in ['id', 'tank_id']]

    if not numeric_params:
        st.info(translate("No numeric parameters found for") + f" {tank_name} to perform analytics.")
        return

    # --- Widget Definition Map ---
    # A dictionary mapping internal panel keys to their display labels and
    # corresponding rendering functions. This facilitates dynamic panel rendering.
    WIDGETS: Dict[str, Tuple[str, Callable]] = {
        "interactive": ("🔬 Interactive Dashboard", render_interactive_dashboard),
        "raw_data": ("🗂️ Raw Data Table", render_raw_data_table),
        "rolling_avg": ("🔄 30-Day Rolling Averages", render_rolling_averages),
        "correlation": ("🔗 Correlation Matrix", render_correlation_matrix),
        "scatter": ("🔍 Scatter & Regression", render_scatter_regression),
        "forecast": ("📈 7-Day Forecast", render_forecast),
        "anomaly_detection": ("🚨 Anomaly Detection", render_anomaly_detection),
    }
    
    # --- UI Rendering Controls ---
    with st.expander("🔧 Visualisation Controls", expanded=True):
        # Date range selector for filtering the data displayed in the panels
        selected_date_range = st.date_input(
            translate("Select Date Range"), value=[min_date, max_date],
            min_value=min_date, max_value=max_date, key="vis_date_range"
        )
        
        # Read the panel selection from st.session_state.dashboard_panels, which is
        # managed by the multiselect in sidebar/settings_panel.py.
        # Provide a default if it's not set yet (e.g., on first load before settings are opened).
        initial_dashboard_panels_default = [k for k in WIDGETS.keys() if k != 'interactive']
        selected_panels_from_settings = st.session_state.get("dashboard_panels", initial_dashboard_panels_default)

        # Allow user to refine/reorder panels from the settings.
        st.session_state.dashboard_panels_display_order = st.multiselect(
            "Select other analytics panels to display:",
            options=[k for k in WIDGETS.keys() if k != 'interactive'], # Exclude interactive as it's always shown
            default=selected_panels_from_settings,
            format_func=lambda key: WIDGETS[key][0],
            key="dashboard_panels_multiselect_display" # Changed key to avoid conflict and indicate its purpose
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

    # Always render the new interactive dashboard first (it's the primary view now)
    render_interactive_dashboard(vis_df, numeric_params)

    # Loop through the user's selections and render the other panels.
    # Use the value from the new display order multiselect, or fall back to the settings one.
    panels_to_render = st.session_state.get("dashboard_panels_multiselect_display", selected_panels_from_settings)
    
    for panel_key in panels_to_render:
        if panel_key in WIDGETS and panel_key != "interactive":
            _label, render_func = WIDGETS[panel_key]
            # Pass specific arguments based on the panel type
            if panel_key == 'raw_data':
                render_func(vis_df, tank_name, start_date, end_date)
            else:
                render_func(vis_df, numeric_params)