# utils/ui/charts.py

"""
charts.py – UI Charting Functions

Provides UI-specific helper functions for creating standardized charts. Contains
logic for generating multi-parameter line charts with Altair and cleaning
DataFrames for visualization.
"""

from __future__ import annotations

import pandas as pd
import altair as alt
import streamlit as st

from config import SAFE_RANGES

# ————————————————————————————————————————————————
# Known numeric measurement keys
# ————————————————————————————————————————————————

KNOWN_NUMERIC = {
    "ph", "ammonia", "nitrite", "nitrate",
    "temperature", "kh", "gh",
}


def clean_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Copy *df* and coerce KNOWN_NUMERIC cols to floats and 'date' to datetime.
    Any un-coercible values become NaN.
    """
    df2 = df.copy()
    for col in KNOWN_NUMERIC.intersection(df2.columns):
        df2[col] = pd.to_numeric(df2[col], errors="coerce")
    if "date" in df2.columns:
        df2["date"] = pd.to_datetime(df2["date"], errors="coerce")
    return df2


def rolling_summary(df: pd.DataFrame, param: str, window_days: int = 30) -> pd.DataFrame:
    """30-day rolling mean for a given parameter."""
    df2 = clean_numeric_df(df).set_index("date").sort_index()
    roll = (
        df2[param]
           .rolling(f"{window_days}D", min_periods=1)
           .mean()
           .reset_index()
           .rename(columns={param: f"{param}_roll{window_days}"})
    )
    return roll


def multi_param_line_chart(df: pd.DataFrame, params: list[str]) -> None:
    """Multi‑parameter line chart with *out‑of‑range* overlays and diagnostics."""
    if df.empty or not params:
        st.info("No data to display.")
        return

    df_cleaned = clean_numeric_df(df)
    # Only genuinely numeric cols
    numeric_params_for_melt = [
        p for p in params
        if p in df_cleaned.columns and pd.api.types.is_numeric_dtype(df_cleaned[p])
    ]
    if not numeric_params_for_melt:
        st.info("No numeric parameters selected.")
        return

    # Melt wide→long
    df2 = df_cleaned.melt(
        id_vars=["date"],
        value_vars=numeric_params_for_melt,
        var_name="parameter",
        value_name="value",
    )

    # Final coercion + diagnostics
    df2["value"] = pd.to_numeric(df2["value"], errors="coerce")
    print("charts.py: df2['value'] dtype after coercion:", df2["value"].dtype)
    types = df2["value"].apply(lambda v: type(v)).unique()
    print("charts.py: sample value types after coercion:", types)

    bad = df2["value"].isna()
    if bad.any():
        print("⚠️ Dropping non-numeric rows in charts.py →", df2.loc[bad].head(3))
    df2 = df2.dropna(subset=["value"])

    if df2.empty:
        st.warning("All selected parameters contained only non‑numeric values.")
        return

    # Base line chart
    base = (
        alt.Chart(df2)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("parameter:N", title="Parameter"),
            tooltip=["date:T", "parameter:N", alt.Tooltip("value:Q", format=".2f")],
        )
        .properties(height=300)
    )

    # Out-of-range overlays with type-check
    overlays: list[alt.Chart] = []
    for p in numeric_params_for_melt:
        lo_hi = SAFE_RANGES.get(p)
        if lo_hi is None:
            continue
        try:
            lo, hi = float(lo_hi[0]), float(lo_hi[1])
        except Exception:
            print(f"⚠️ SAFE_RANGES for '{p}' not numeric → {lo_hi!r}")
            continue
        subset = df2[df2["parameter"] == p]
        try:
            out = subset[(subset["value"] < lo) | (subset["value"] > hi)]
        except TypeError as e:
            print(f"❌ TypeError for param '{p}': lo={lo}, hi={hi}")
            print("subset['value'] dtype:", subset["value"].dtype)
            print("subset sample types:", subset["value"].apply(lambda v: type(v)).unique())
            raise
        if not out.empty:
            overlays.append(
                alt.Chart(out)
                .mark_circle(size=100, color="red")
                .encode(
                    x="date:T",
                    y="value:Q",
                    tooltip=["date:T", "parameter:N", alt.Tooltip("value:Q", format=".2f")],
                )
            )

    # Combine and render
    chart = base
    for o in overlays:
        chart += o
    st.altair_chart(chart, use_container_width=True)

print("📈 charts.py re-loaded at runtime – id:", id(multi_param_line_chart))
