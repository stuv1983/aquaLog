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

# ————————————————————————————————————————————————
# Known numeric measurement keys
# A set of parameter names expected to hold numeric measurement values.
# Used for consistent data type coercion across the application.
# ————————————————————————————————————————————————

KNOWN_NUMERIC = {
    "ph", "ammonia", "nitrite", "nitrate",
    "temperature", "kh", "gh",
}


def clean_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a copy of the input DataFrame and coerces specified numeric columns
    (defined in `KNOWN_NUMERIC`) to float and the 'date' column to datetime.
    Any values that cannot be coerced will become NaN (Not a Number) or NaT (Not a Time).

    Args:
        df: The input Pandas DataFrame.

    Returns:
        pd.DataFrame: A new DataFrame with the specified columns cleaned and
                      converted to the correct data types for numerical analysis
                      and plotting.
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
        df: The input Pandas DataFrame containing a 'date' column and the `param` column.
        param: The name of the numeric parameter column for which to calculate the rolling mean.
        window_days: The size of the rolling window in days. Defaults to 30 days.

    Returns:
        pd.DataFrame: A new DataFrame with 'date' and the calculated rolling mean column.
                      The new column is named `{param}_roll{window_days}`.
    """
    # Clean numeric columns and set 'date' as index, then sort by date.
    df2 = clean_numeric_df(df).set_index("date").sort_index()
    
    # Calculate the rolling mean using a time-based window.
    # `min_periods=1` ensures that rolling mean is calculated even if fewer data points
    # than the window size are available at the beginning of the series.
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
    data points that are outside the configured safe ranges.

    Args:
        df: The input Pandas DataFrame containing historical water test data.
            Expected to have a 'date' column and various parameter columns.
        params: A list of parameter names (column names in df) to include in the chart.
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
    # This is required by Altair to plot multiple lines based on a 'parameter' column.
    df2 = df_cleaned.melt(
        id_vars=["date"], # Identifier variable (column to keep as-is)
        value_vars=numeric_params_for_melt, # Columns to unpivot
        var_name="parameter", # New column for original column names
        value_name="value", # New column for values
    )

    # Final coercion to numeric and handle missing values for robustness.
    df2["value"] = pd.to_numeric(df2["value"], errors="coerce")
    
    # Debugging print statements (can be removed in production)
    # print("charts.py: df2['value'] dtype after coercion:", df2["value"].dtype)
    # types = df2["value"].apply(lambda v: type(v)).unique()
    # print("charts.py: sample value types after coercion:", types)

    bad = df2["value"].isna()
    if bad.any():
        # print("⚠️ Dropping non-numeric rows in charts.py →", df2.loc[bad].head(3))
        pass # Suppress print for cleaner output unless debugging
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
            # print(f"⚠️ SAFE_RANGES for '{p}' not numeric → {lo_hi!r}")
            continue # Skip if safe range values are not numeric
        
        subset = df2[df2["parameter"] == p] # Filter data for the current parameter
        try:
            # Identify data points outside the safe range for this parameter.
            out = subset[(subset["value"] < lo) | (subset["value"] > hi)]
        except TypeError as e:
            # More detailed debugging for TypeError during comparison (e.g., comparing string with float)
            # print(f"❌ TypeError for param '{p}': lo={lo}, hi={hi}")
            # print("subset['value'] dtype:", subset["value"].dtype)
            # print("subset sample types:", subset["value"].apply(lambda v: type(v)).unique())
            raise # Re-raise if this error occurs, as it indicates a data type issue.
        
        if not out.empty:
            # Create a circle mark for out-of-range points.
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
    
    st.altair_chart(chart, use_container_width=True) # Render the final combined chart

# Debugging print statement to track module reloading (can be removed in production)
# print("📈 charts.py re-loaded at runtime – id:", id(multi_param_line_chart))