# tabs/failed_tests_tab.py
"""
tabs/failed_tests_tab.py – multi‑tank aware ⚠️
This tab lists EVERY historical test where at least one parameter is outside
the configured SAFE_RANGES (defined in config.py). All queries are now
scoped to the **selected tank** via st.session_state["tank_id"] (fallback = 1).
"""

from __future__ import annotations

import datetime as _dt
import pandas as _pd
import streamlit as st

# 1. Import repositories instead of legacy functions
from aqualog_db.repositories import TankRepository, WaterTestRepository

from utils import clean_numeric_df, is_mobile, translate, format_with_units
from config import SAFE_RANGES
from components import highlight_out_of_range

# Removed debug print statement: print(">>> LOADING", __file__,)

# ─────────────────────────────────────────────────────────────────────────────
# Helper – get tank‑scoped dataframe of *failed* tests only
# ─────────────────────────────────────────────────────────────────────────────

def _load_failed_tests(tank_id: int | None) -> _pd.DataFrame:
    """
    Loads all water test records for a given tank and filters them to return
    only those records where at least one parameter is outside its defined
    `SAFE_RANGES`.

    The function ensures numeric types for comparison and handles potential
    missing values during filtering.

    Args:
        tank_id (int | None): The ID of the tank to load failed tests for.
                              If None, the underlying `fetch_by_date_range`
                              would typically return data for all tanks, but
                              in this context, a valid tank_id is always expected.

    Returns:
        _pd.DataFrame: A Pandas DataFrame containing only the water test records
                       that have at least one out-of-range parameter.
                       Returns an empty DataFrame if no such tests are found.
    """
    # Define end date as today for the query.
    end_iso = _dt.date.today().isoformat() + "T23:59:59"

    # Instantiate the repository and call its method to fetch all data for the tank.
    water_test_repo = WaterTestRepository()
    # Fetches all water tests from a very early date to today for the specified tank.
    df = water_test_repo.fetch_by_date_range("1970-01-01T00:00:00", end_iso, tank_id)

    if df.empty:
        return df

    # Ensure numeric conversion for all known measurement columns to prevent comparison errors.
    # This also handles columns not being perfectly numeric due to data entry.
    numeric_df = clean_numeric_df(df)
    
    # Coerce all columns relevant to SAFE_RANGES to numeric to avoid string/float comparisons.
    # Non-numeric values will become NaN after coercion.
    for col in SAFE_RANGES:
        if col in numeric_df.columns:
            numeric_df[col] = _pd.to_numeric(numeric_df[col], errors='coerce')

    # Initialize a boolean mask to identify rows with any out-of-range value.
    mask = _pd.Series(False, index=numeric_df.index)
    # Iterate through each parameter and its safe range to build the mask.
    for col, (low, high) in SAFE_RANGES.items():
        if col in numeric_df.columns:
            # Check if value is less than low OR greater than high.
            mask |= (numeric_df[col] < low) | (numeric_df[col] > high)
            
    return numeric_df[mask] # Return only the rows that are out of range

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit tab renderer
# ─────────────────────────────────────────────────────────────────────────────

def failed_tests_tab() -> None:
    """
    Renders the "Failed Tests" tab in the Streamlit application.

    This tab provides a historical overview of all water test records for the
    currently selected tank where one or more parameters were outside their
    configured safe ranges. It displays this information
    in a tabular view with visual highlighting of out-of-range values.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    # Determine the active tank ID from session state, defaulting to 1.
    tank_id = st.session_state.get("tank_id", 1)
    
    # Instantiate the TankRepository to get the tank's friendly name.
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    # Get the tank name for display in the header.
    tank_name = next((t['name'] for t in tanks if t['id'] == tank_id), f"Tank #{tank_id}")

    # Header for the tab.
    st.header(f"⚠️ {translate('Failed Tests')} — {tank_name}")

    # Load the DataFrame containing only out-of-range test results.
    df_failed = _load_failed_tests(tank_id)
    if df_failed.empty:
        # Inform the user if no out-of-range tests are found.
        st.info(translate("No out‑of‑range water tests for") + f" {tank_name}.")
        return

    # Prepare a copy of the DataFrame for display purposes.
    display_df = df_failed.copy()
    
    # Format specific columns with units for better readability.
    # Applies `format_with_units` helper to temperature, GH, and KH columns.
    if "temperature" in display_df.columns:
        display_df["temperature"] = display_df["temperature"].apply(
            lambda v: format_with_units(v, "temperature") if _pd.notnull(v) else "N/A"
        )
    if "gh" in display_df.columns:
        display_df["gh"] = display_df["gh"].apply(
            lambda v: format_with_units(v, "gh") if _pd.notnull(v) else "N/A"
        )
    if "kh" in display_df.columns:
        display_df["kh"] = display_df["kh"].apply(
            lambda v: format_with_units(v, "kh") if _pd.notnull(v) else "N/A"
        )

    # Localize and rename headers for display, using the `translate` utility.
    rename_map = {c: translate(c.capitalize()) for c in display_df.columns}
    # Specific override for GH and KH display labels for consistent unit notation.
    if "gh" in rename_map:
        rename_map["gh"] = "GH (°dH)"
    if "kh" in rename_map:
        rename_map["kh"] = "KH (°dKH)"
    # Apply renaming to the display DataFrame.
    display_df.rename(columns=rename_map, inplace=True)

    # Apply conditional highlighting to out-of-range cells in the DataFrame using `highlight_out_of_range`.
    styled = highlight_out_of_range(display_df, SAFE_RANGES)

    # Display the styled table.
    # On mobile devices, the table is wrapped in an expander for better screen real estate management.
    if is_mobile():
        with st.expander(translate("Show Failed Tests"), expanded=False):
            st.dataframe(styled, use_container_width=True)
    else:
        st.dataframe(styled, use_container_width=True)