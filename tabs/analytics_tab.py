"""
analytics_tab.py – Analytics & Reporting (v3.3.0)
Renders rolling averages, correlation matrices, scatter/regression analyses,
and a 7-day Holt-Winters forecast for selected parameters.
Updated: 2025-06-10

"""
import datetime               # For handling dates and time deltas
import pandas as pd           # Pandas for DataFrame manipulation
import streamlit as st        # Streamlit for UI components
import altair as alt          # Altair for interactive charts

# Fetch data from SQLite and get raw connection if needed
from db import fetch_data, get_connection
# Utility functions: detect mobile viewport, show warnings, clean and type-cast data
from utils import is_mobile, show_out_of_range_banner, clean_numeric_df
# Configuration: safe parameter ranges
from config import SAFE_RANGES


def analytics_tab():
    """
    Render the "Analytics & Reporting" tab, which includes:
    - Displaying any out-of-range warnings from the latest test
    - Date pickers for filtering data range
    - 30-day rolling average charts for numeric parameters
    - Correlation matrix for numeric parameters
    - Scatter plot with regression line for chosen X/Y parameters
    - Optional 7-day forecast using Holt-Winters Exponential Smoothing
    """
    # Header for the tab
    st.header("📊 Analytics & Reporting")
    # Show persistent out-of-range banner (with suffix to keep separate state per tab)
    # show_out_of_range_banner("analytics")

    # ──────────────────────────────────────────────────────────────────────────
    # Retrieve overall min/max dates from water_tests to set up date selector bounds
    # ──────────────────────────────────────────────────────────────────────────
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MIN(date), MAX(date) FROM water_tests;")
    row = cur.fetchone()
    conn.close()
    # If there are no records at all, display an info message and exit
    if not row or row[0] is None:
        st.info("No data available.")
        return

    # Convert ISO-format strings to date objects for use in date_input
    min_date = datetime.datetime.fromisoformat(row[0]).date()
    max_date = datetime.datetime.fromisoformat(row[1]).date()

    # ──────────────────────────────────────────────────────────────────────────
    # Date inputs: allow user to select a start and end date within available range
    # Behavior changes slightly on mobile (shorter label)
    # ──────────────────────────────────────────────────────────────────────────
    if is_mobile():
        start_date = st.date_input(
            "Start", key="analytics_start", min_value=min_date,
            max_value=max_date, value=min_date
        )
        end_date = st.date_input(
            "End", key="analytics_end", min_value=min_date,
            max_value=max_date, value=max_date
        )
    else:
        start_date = st.date_input(
            "Start Date", key="analytics_start", min_value=min_date,
            max_value=max_date, value=min_date
        )
        end_date = st.date_input(
            "End Date", key="analytics_end", min_value=min_date,
            max_value=max_date, value=max_date
        )

    # Validate that start_date is not after end_date
    if start_date > end_date:
        st.error("Start Date must be on or before End Date.")
        return

    # ──────────────────────────────────────────────────────────────────────────
    # Fetch filtered data from database and preprocess
    # ──────────────────────────────────────────────────────────────────────────
    df = fetch_data(start_date.isoformat(), end_date.isoformat())
    if df.empty:
        st.info("No data in selected range.")
        return

    # Convert data to correct dtypes and drop any rows with invalid dates
    df = clean_numeric_df(df).dropna(subset=["date"])
    # Identify numeric parameter columns (exclude date, notes, id if present)
    numeric_params = [c for c in df.columns if c not in ("date", "notes", "id")]
    if not numeric_params:
        st.info("No numeric data to analyze.")
        return

    # ── 30-Day Rolling Averages ───────────────────────────────────────────────
    with st.expander("🔄 30-Day Rolling Averages", expanded=not is_mobile()):
        # Allow user to select one or more parameters ("All" means every numeric column)
        options = ["All"] + numeric_params
        selected = st.multiselect(
            "Select parameter(s)", options, default=["All"], key="roll_params"
        )
        # Determine which columns to compute rolling average on
        if "All" in selected:
            selected_roll = numeric_params
        else:
            selected_roll = [p for p in selected if p in numeric_params]

        if selected_roll:
            # Re-index DataFrame by date for time-based rolling calculation
            df_idx = df.set_index("date")
            all_roll = []
            # Compute 30-day rolling mean for each selected parameter
            for param in selected_roll:
                roll_ser = (
                    df_idx[param]
                    .rolling("30D", min_periods=1)
                    .mean()
                    .reset_index()
                    .rename(columns={param: "value"})
                )
                roll_ser["param"] = param
                all_roll.append(roll_ser)
            # Concatenate all series into one DataFrame for plotting
            combined = pd.concat(all_roll, ignore_index=True)
            # Build Altair line chart: date on X, rolling value on Y, colored by parameter
            chart = (
                alt.Chart(combined)
                .mark_line(point=False)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("value:Q", title="30-Day Avg"),
                    color=alt.Color("param:N", title="Parameter"),
                    tooltip=["date:T", "param:N", alt.Tooltip("value:Q", format=".2f")],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

    # ── Correlation Matrix ───────────────────────────────────────────────────
    with st.expander("🔗 Correlation Matrix", expanded=not is_mobile()):
        try:
            # Compute pairwise correlation among numeric columns
            corr = df[numeric_params].corr()
            st.dataframe(corr, use_container_width=True)
        except Exception:
            st.error("Unable to compute correlation matrix.")

    # ── Scatter & Regression ──────────────────────────────────────────────────
    with st.expander("🔍 Scatter & Regression", expanded=not is_mobile()):
        # Let user pick X and Y parameters for scatter plot
        xcol = st.selectbox("X-axis", numeric_params, index=0, key="scatter_x")
        ycol = st.selectbox(
            "Y-axis", numeric_params,
            index=1 if len(numeric_params) > 1 else 0,
            key="scatter_y"
        )
        # Filter out rows missing either X or Y
        df_sc = df.dropna(subset=[xcol, ycol])
        if not df_sc.empty:
            try:
                # Base scatter chart with circles
                scatter = (
                    alt.Chart(df_sc)
                    .mark_circle(size=60)
                    .encode(
                        x=alt.X(f"{xcol}:Q", title=xcol.capitalize()),
                        y=alt.Y(f"{ycol}:Q", title=ycol.capitalize()),
                        tooltip=["date", xcol, ycol],
                    )
                )
                # Add a regression line (in red) on top
                reg = scatter.transform_regression(xcol, ycol).mark_line(color="red")
                st.altair_chart(scatter + reg, use_container_width=True)
            except Exception:
                st.error("Unable to render scatter/regression chart.")
        else:
            # Inform user if not enough paired data points
            st.write("Not enough data for scatter/regression.")

    # ── 7-Day Forecast ────────────────────────────────────────────────────────
    with st.expander("📈 7-Day Forecast", expanded=not is_mobile()):
        # User selects which parameter to forecast
        xcol_fc = st.selectbox("Forecast parameter", numeric_params, index=0, key="forecast_param")
        # Extract historical series (indexed by date) and drop missing values
        series = df.set_index("date")[xcol_fc].dropna()
        if len(series) < 2:
            st.warning("Not enough data to forecast.")
        else:
            try:
                # Dynamically import Holt-Winters model from statsmodels
                from statsmodels.tsa.holtwinters import ExponentialSmoothing

                # Fit an additive trend model (no seasonality)
                model = ExponentialSmoothing(series, trend="add", seasonal=None).fit(optimized=True)
                # Forecast the next 7 days
                forecast = model.forecast(7)
                last_date = series.index.max()
                # Generate future date index for plotting
                fut_dates = pd.date_range(
                    last_date + datetime.timedelta(days=1), periods=7, freq="D"
                )
                # Build a DataFrame with forecasted values
                fc_df = pd.DataFrame({
                    "date": fut_dates,
                    "value": forecast.values,
                    "type": "forecast"
                })
                # Also prepare historical DataFrame for combined plotting
                hist_df = series.reset_index().rename(columns={xcol_fc: "value"})
                hist_df["type"] = "historical"
                # Combine historical and forecast data
                plot_df = pd.concat([hist_df, fc_df], ignore_index=True)

                # Create a line chart differentiating historical vs. forecast
                line = (
                    alt.Chart(plot_df)
                    .mark_line()
                    .encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("value:Q", title=xcol_fc.capitalize()),
                        color=alt.Color("type:N", title="Type"),
                        tooltip=["date", "type", alt.Tooltip("value:Q", format=".2f")],
                    )
                    .properties(height=300)
                )
                st.altair_chart(line, use_container_width=True)
            except Exception:
                st.error("Forecasting failed—ensure statsmodels is installed.")
