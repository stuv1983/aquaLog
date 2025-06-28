# utils/ui/charts.py

"""
charts.py – UI Charting Functions

Provides UI-specific helper functions for creating standardized charts. Contains
logic for generating multi-parameter line charts with Altair and cleaning
DataFrames for visualization, ensuring data is in the correct format for plotting.
"""

from __future__ import annotations

import pandas as pd
import altair as alt
import streamlit as st

from config import SAFE_RANGES

# ────────────────────────────────────────────────────────────────
# Known numeric measurement keys
# ────────────────────────────────────────────────────────────────
KNOWN_NUMERIC: set[str] = {
    """
    A set of parameter names (column keys) that are expected to hold numeric
    measurement values in DataFrames.
    This set is used for consistent data type coercion across the application's
    charting and analytical functions, ensuring numerical columns are treated
    as floats for plotting.
    """
    "ph", "ammonia", "nitrite", "nitrate",
    "temperature", "kh", "gh",
}


def clean_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a copy of the input DataFrame and coerces specified numeric columns
    (those present in `KNOWN_NUMERIC`) to `float` and the 'date' column to `datetime`.
    Any values that cannot be coerced (e.g., non-numeric strings in a numeric column)
    will become `NaN` (Not a Number) or `NaT` (Not a Time) respectively.

    Args:
        df (pd.DataFrame): The input Pandas DataFrame.

    Returns:
        pd.DataFrame: A new DataFrame (a copy of the original) with the specified
                      columns cleaned and converted to the correct data types
                      for numerical analysis and plotting.
    """
    df2 = df.copy() # Work on a copy to avoid modifying the original DataFrame
    for col in KNOWN_NUMERIC.intersection(df2.columns):
        # Coerce numeric columns to float, turning errors into NaN.
        df2[col] = pd.to_numeric(df2[col], errors="coerce")
    if "date" in df2.columns:
        # Coerce 'date' column to datetime, turning errors into NaT.
        df2["date"] = pd.to_datetime(df2["date"], errors="coerce")
    return df2


def rolling_summary(df: pd.DataFrame, param: str, window_days: int = 30) -> pd.DataFrame:
    """
    Calculates the rolling mean for a given parameter over a specified window (in days).

    This function is useful for smoothing out short-term fluctuations and highlighting
    longer-term trends in water quality data.

    Args:
        df (pd.DataFrame): The input Pandas DataFrame containing a 'date' column
                           (as datetime) and the `param` column (as numeric).
        param (str): The name of the numeric parameter column for which to calculate the rolling mean.
        window_days (int): The size of the rolling window in days. Defaults to 30 days.

    Returns:
        pd.DataFrame: A new DataFrame with 'date' and the calculated rolling mean column.
                      The new column is named `{param}_roll{window_days}`.
    """
    # Clean numeric columns and set 'date' as index, then sort by date.
    df2 = clean_numeric_df(df).set_index("date").sort_index()
    
    # Calculate the rolling mean using a time-based window.
    # `min_periods=1` ensures that the rolling mean is calculated even if fewer data points
    # than the full `window_days` are available at the beginning of the series.
    roll = (
        df2[param]
           .rolling(f"{window_days}D", min_periods=1)
           .mean()
           .reset_index() # Convert the Series back to a DataFrame with 'date' column
           .rename(columns={param: f"{param}_roll{window_days}"}) # Rename the rolling mean column
    )
    return roll


def multi_param_line_chart(df: pd.DataFrame, params: list[str]) -> None:
    """
    Generates and displays a multi-parameter line chart using Altair.

    The chart includes interactive points and optional overlays to highlight
    data points that are outside the configured safe ranges from `config.SAFE_RANGES`.

    Args:
        df (pd.DataFrame): The input Pandas DataFrame containing historical water test data.
                           Expected to have a 'date' column (datetime) and various parameter columns.
        params (list[str]): A list of parameter names (column names in `df`) to include in the chart.

    Returns:
        None: This function renders a Streamlit Altair chart and does not return any value.
    """
    if df.empty or not params:
        st.info("No data to display or no parameters selected for charting.")
        return

    df_cleaned = clean_numeric_df(df) # Ensure data types are correct for plotting
    
    # Filter for genuinely numeric columns among the selected parameters.
    numeric_params_for_melt = [
        p for p in params
        if p in df_cleaned.columns and pd.api.types.is_numeric_dtype(df_cleaned[p])
    ]
    if not numeric_params_for_melt:
        st.info("No numeric parameters selected for charting.")
        return

    # Melt the DataFrame from wide to long format.
    # This transforms columns like 'ph', 'ammonia', 'nitrite' into rows,
    # creating new 'parameter' and 'value' columns. This format is required
    # by Altair to easily assign 'parameter' to color and 'value' to the Y-axis
    # for multiple lines.
    df2 = df_cleaned.melt(
        id_vars=["date"], # Identifier variable (column to keep as-is)
        value_vars=numeric_params_for_melt, # Columns to unpivot
        var_name="parameter", # New column for original column names
        value_name="value", # New column for values
    )

    # Final coercion to numeric and handle missing values for robustness.
    # Any values that couldn't be coerced to numeric are dropped.
    df2["value"] = pd.to_numeric(df2["value"], errors="coerce")
    
    # Removed debugging print statements.
    df2 = df2.dropna(subset=["value"]) # Drop rows where 'value' could not be coerced to numeric

    if df2.empty:
        st.warning("All selected parameters contained only non‑numeric values after cleaning, so no chart can be displayed.")
        return

    # Base line chart definition using Altair.
    base = (
        alt.Chart(df2)
        .mark_line(point=True) # Draw lines and points for each data point
        .encode(
            x=alt.X("date:T", title="Date"), # Temporal axis
            y=alt.Y("value:Q", title="Value"), # Quantitative axis
            color=alt.Color("parameter:N", title="Parameter"), # Color lines by parameter
            tooltip=["date:T", "parameter:N", alt.Tooltip("value:Q", format=".2f")], # Tooltip on hover
        )
        .properties(height=300) # Set chart height
    )

    # Out-of-range overlays: circles to mark anomalous data points.
    overlays: list[alt.Chart] = []
    for p in numeric_params_for_melt:
        lo_hi = SAFE_RANGES.get(p)
        if lo_hi is None:
            continue # Skip if no safe range is defined for the parameter
        try:
            lo, hi = float(lo_hi[0]), float(lo_hi[1]) # Ensure bounds are floats
        except Exception:
            # Skip if safe range values are not numeric (though they should be defined as such in config.py).
            continue
        
        subset = df2[df2["parameter"] == p] # Filter data for the current parameter
        try:
            # Identify data points falling outside the safe range for this parameter.
            out = subset[(subset["value"] < lo) | (subset["value"] > hi)]
        except TypeError: # Catch TypeError if comparison fails (e.g., non-numeric data somehow slipped through)
            # Re-raise here if this error occurs, as it indicates a fundamental data type issue.
            # In a deployed app, this might be a more user-friendly error or robust NaN handling.
            raise
        
        if not out.empty:
            # Create a red circle mark for each out-of-range data point.
            overlays.append(
                alt.Chart(out)
                .mark_circle(size=100, color="red") # Red circles for warnings
                .encode(
                    x="date:T",
                    y="value:Q",
                    tooltip=["date:T", "parameter:N", alt.Tooltip("value:Q", format=".2f")],
                )
            )

    # Combine the base line chart with all generated overlays.
    chart = base
    for o in overlays:
        chart += o
    
    st.altair_chart(chart, use_container_width=True)