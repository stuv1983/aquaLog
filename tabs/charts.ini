"""charts.py – shared chart helpers for AquaLog

This file **must** be located where your `data_analytics_tab` imports it, e.g.:
    from charts import multi_param_line_chart

If your project instead imports `utils.ui.charts`, rename / move accordingly –
the important thing is that *this* exact code is the one Python actually loads
at runtime.
"""

from __future__ import annotations

import pandas as pd
import altair as alt
import streamlit as st

from config import SAFE_RANGES

# ————————————————————————————————————————————————
# Helper: coerce all potential numeric columns
# ————————————————————————————————————————————————


KNOWN_NUMERIC = {
    "ph",
    "ammonia",
    "nitrite",
    "nitrate",
    "temperature",
    "kh",
    "gh",
    # add any new measurement keys here →
}


def clean_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a *copy* of *df* where KNOWN_NUMERIC columns are floats and
    *date* is a proper ``datetime64[ns]``. Any value that can’t be coerced to a
    float becomes ``NaN``.
    """

    df2 = df.copy()

    # Coerce known numeric columns
    for col in KNOWN_NUMERIC.intersection(df2.columns):
        df2[col] = pd.to_numeric(df2[col], errors="coerce")

    if "date" in df2.columns:
        df2["date"] = pd.to_datetime(df2["date"], errors="coerce")

    return df2


# ————————————————————————————————————————————————
# Rolling summary (used by 30‑day averages panel)
# ————————————————————————————————————————————————


def rolling_summary(df: pd.DataFrame, param: str, window_days: int = 30) -> pd.DataFrame:
    df2 = clean_numeric_df(df).set_index("date").sort_index()
    roll = (
        df2[param]
        .rolling(f"{window_days}D", min_periods=1)
        .mean()
        .reset_index()
        .rename(columns={param: f"{param}_roll{window_days}"})
    )
    return roll


# ————————————————————————————————————————————————
# Main chart used in *Data & Analytics* tab
# ————————————————————————————————————————————————


def multi_param_line_chart(df: pd.DataFrame, params: list[str]) -> None:  # noqa: C901 – acceptable length
    """Multi‑parameter line chart with *out‑of‑range* overlays.

    Any parameter whose **SAFE_RANGES** entry is missing simply renders without
    the red‑dot out‑of‑range markers.
    """

    if df.empty or not params:
        st.info("No data to display.")
        return

    df_cleaned = clean_numeric_df(df)

    # Keep only columns that ended up genuinely numeric after coercion
    numeric_params_for_melt = [
        p for p in params if p in df_cleaned.columns and pd.api.types.is_numeric_dtype(df_cleaned[p])
    ]

    if not numeric_params_for_melt:
        st.info("No numeric parameters selected to display in the chart.")
        return

    # — Melt wide → long —
    df2 = df_cleaned.melt(
        id_vars=["date"],
        value_vars=numeric_params_for_melt,
        var_name="parameter",
        value_name="value",
    )

    # Final coercion + sanity‑check *right here*, drop non‑numeric rows
    df2["value"] = pd.to_numeric(df2["value"], errors="coerce")
    bad_rows = df2["value"].isna()

    if bad_rows.any():
        # For debugging: print one offending example to the Streamlit log
        sample_bad = df2.loc[bad_rows].head(3)
        print("⚠️ Dropping non‑numeric rows in charts.py →\n", sample_bad)

    df2 = df2.dropna(subset=["value"])

    # If after dropping we have no data, bail out gracefully
    if df2.empty:
        st.warning("All selected parameters contained only non‑numeric values after coercion.")
        return

    # — Base line chart —
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

    # — Out‑of‑range overlays —
    overlays = []
    for p in numeric_params_for_melt:
        lo_hi = SAFE_RANGES.get(p)
        if lo_hi is None:
            continue
        lo, hi = lo_hi
        subset = df2[df2["parameter"] == p]
        out = subset[(subset["value"] < lo) | (subset["value"] > hi)]
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

    chart = base
    for overlay in overlays:
        chart += overlay

    st.altair_chart(chart, use_container_width=True)


print("📈 charts.py re‑loaded at runtime – id:", id(multi_param_line_chart))
