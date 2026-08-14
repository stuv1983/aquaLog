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

from utils import clean_numeric_df, is_mobile, translate, format_with_units, is_out_of_range
from config import SAFE_RANGES
from components import highlight_out_of_range

# Removed debug print statement: print(">>> LOADING", __file__,)

# ─────────────────────────────────────────────────────────────────────────────
# Helper – get tank‑scoped dataframe of *failed* tests only
# ─────────────────────────────────────────────────────────────────────────────

def _co2_failure_mask(df: _pd.DataFrame, tank_id: int | None) -> _pd.Series:
    """
    Builds a boolean mask flagging rows whose ``co2_indicator`` reading counts as
    a failure, using the canonical `utils.validation.is_out_of_range` validator.

    Delegating to the validator keeps this tab consistent with the Warnings tab:
    "Blue" is suppressed outside the tank's CO₂ injection window, and tanks with
    CO₂ disabled never fail on this parameter. Because the CO₂ verdict depends
    only on the colour and the hour of the test, results are memoised per
    (colour, hour) pair so the validator's per-call DB lookups run at most a
    handful of times instead of once per row.

    Args:
        df (_pd.DataFrame): Water test rows. Must contain a ``co2_indicator``
                            column; an optional ``date`` column supplies the
                            test timestamp used for schedule-aware suppression.
        tank_id (int | None): The tank the readings belong to. When None, no row
                              can be evaluated and an all-False mask is returned.

    Returns:
        _pd.Series: A boolean Series aligned with `df.index`, True where the
                    CO₂ reading is out of range.
    """
    empty_mask = _pd.Series(False, index=df.index, dtype=bool)
    if tank_id is None or "co2_indicator" not in df.columns:
        return empty_mask

    # `clean_numeric_df` already coerces 'date' to datetime, but this helper is
    # cheap enough to re-run and keeps the function usable on raw frames too.
    if "date" in df.columns:
        timestamps = _pd.to_datetime(df["date"], errors="coerce").tolist()
    else:
        timestamps = [None] * len(df)

    cache: dict[tuple[str, int | None], bool] = {}
    flags: list[bool] = []
    for raw_value, timestamp in zip(df["co2_indicator"].tolist(), timestamps):
        # Blank / missing readings are simply "not tested", never a failure.
        if not isinstance(raw_value, str) or not raw_value.strip():
            flags.append(False)
            continue

        value = raw_value.strip()
        test_time = timestamp.time() if timestamp is not None and _pd.notna(timestamp) else None
        key = (value, test_time.hour if test_time is not None else None)
        if key not in cache:
            cache[key] = bool(
                is_out_of_range(
                    "co2_indicator",
                    value,
                    tank_id=tank_id,
                    test_time=test_time,
                )
            )
        flags.append(cache[key])

    return _pd.Series(flags, index=df.index, dtype=bool)


def _load_failed_tests(tank_id: int | None) -> _pd.DataFrame:
    """
    Loads all water test records for a given tank and filters them to return
    only those records where at least one parameter is outside its defined
    `SAFE_RANGES`.

    Numeric parameters are compared directly against `SAFE_RANGES`, while the
    categorical `co2_indicator` is evaluated by `is_out_of_range()` (see
    `_co2_failure_mask`) so that CO₂ schedule and per-tank CO₂ settings are
    respected exactly as they are on the Warnings tab.

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
    # co2_indicator is deliberately excluded: it is categorical (Green/Blue/Yellow)
    # and coercing it would destroy the very values `_co2_failure_mask` needs.
    for col in SAFE_RANGES:
        if col == "co2_indicator":
            continue
        if col in numeric_df.columns:
            numeric_df[col] = _pd.to_numeric(numeric_df[col], errors='coerce')

    # Initialize a boolean mask to identify rows with any out-of-range value.
    mask = _pd.Series(False, index=numeric_df.index)
    # Iterate through each parameter and its safe range to build the mask.
    for col, (low, high) in SAFE_RANGES.items():
        # Handled below by the canonical validator, which is schedule-aware.
        if col == "co2_indicator":
            continue
        if col in numeric_df.columns:
            # Check if value is less than low OR greater than high.
            mask |= (numeric_df[col] < low) | (numeric_df[col] > high)

    # Categorical CO₂ check, delegated to is_out_of_range() so this tab agrees
    # with the Warnings tab on schedule-based and no-CO₂-tank suppression.
    mask |= _co2_failure_mask(numeric_df, tank_id)

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