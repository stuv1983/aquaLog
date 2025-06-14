import pandas as pd
import altair as alt
import streamlit as st
from config import SAFE_RANGES

def clean_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans a DataFrame by converting columns to appropriate numeric types.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Cleaned DataFrame with proper types
    """
    df2 = df.copy().replace({None: pd.NA})
    if "date" in df2.columns:
        df2["date"] = pd.to_datetime(df2["date"], errors="coerce")
    for c in df2.columns:
        if c != "date":
            df2[c] = pd.to_numeric(df2[c], errors='coerce')
    return df2

def rolling_summary(df: pd.DataFrame, param: str, window_days: int = 30) -> pd.DataFrame:
    """
    Calculates rolling averages for a parameter.
    
    Args:
        df: Input DataFrame
        param: Parameter to analyze
        window_days: Rolling window size in days
        
    Returns:
        DataFrame with rolling averages
    """
    df2 = clean_numeric_df(df).set_index("date").sort_index()
    roll = df2[param].rolling(f"{window_days}D", min_periods=1).mean().reset_index()
    roll.rename(columns={param: f"{param}_roll{window_days}"}, inplace=True)
    return roll

def multi_param_line_chart(df: pd.DataFrame, params: list[str]) -> None:
    """
    Creates a multi-parameter line chart with out-of-range highlights.
    
    Args:
        df: Input DataFrame
        params: List of parameters to plot
    """
    if df.empty or not params:
        st.info("No data to display.")
        return
        
    df2 = clean_numeric_df(df).melt(
        id_vars=["date"], 
        value_vars=params, 
        var_name="parameter", 
        value_name="value"
    )
    
    base = alt.Chart(df2).mark_line(point=True).encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("value:Q", title="Value"),
        color=alt.Color("parameter:N", title="Parameter"),
        tooltip=["date:T", "parameter:N", "value:Q"]
    ).properties(height=300)
    
    overlays = []
    for p in params:
        lo_hi = SAFE_RANGES.get(p)
        if lo_hi is None:
            continue
            
        lo, hi = lo_hi
        subset = df2[df2["parameter"] == p].dropna(subset=["value"])
        if subset.empty:
            continue
            
        out = subset[(subset["value"] < lo) | (subset["value"] > hi)]
        if not out.empty:
            overlays.append(
                alt.Chart(out).mark_circle(size=100, color="red").encode(
                    x="date:T", y="value:Q", tooltip=["date:T", "parameter:N", "value:Q"]
                )
            )
    
    chart = base
    for o in overlays:
        chart += o
        
    st.altair_chart(chart, use_container_width=True)