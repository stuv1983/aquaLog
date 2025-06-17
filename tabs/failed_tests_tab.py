# tabs/failed_tests_tab.py (Patched for string-vs-float fix)
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

print(
    ">>> LOADING", __file__,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper – get tank‑scoped dataframe of *failed* tests only
# ─────────────────────────────────────────────────────────────────────────────

def _load_failed_tests(tank_id: int | None) -> _pd.DataFrame:
    """Return a DataFrame of rows where any value is outside SAFE_RANGES."""
    end_iso = _dt.date.today().isoformat() + "T23:59:59"

    # 2. Instantiate the repository and call its method
    water_test_repo = WaterTestRepository()
    df = water_test_repo.fetch_by_date_range("1970-01-01T00:00:00", end_iso, tank_id)

    if df.empty:
        return df

    # Ensure numeric conversion for all known measurement columns
    numeric_df = clean_numeric_df(df)
    # Coerce all SAFE_RANGES columns to numeric to avoid str/float comparisons
    for col in SAFE_RANGES:
        if col in numeric_df.columns:
            numeric_df[col] = _pd.to_numeric(numeric_df[col], errors='coerce')

    mask = _pd.Series(False, index=numeric_df.index)
    for col, (low, high) in SAFE_RANGES.items():
        if col in numeric_df.columns:
            # low/high are numeric in config or will be cast
            mask |= (numeric_df[col] < low) | (numeric_df[col] > high)
    return numeric_df[mask]

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit tab renderer
# ─────────────────────────────────────────────────────────────────────────────

def failed_tests_tab() -> None:
    """Render the **Failed Tests** tab for the selected tank."""
    # Determine active tank and friendly name
    tank_id = st.session_state.get("tank_id", 1)
    
    # 3. Instantiate the repository and call its method
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    tank_name = next((t['name'] for t in tanks if t['id'] == tank_id), f"Tank #{tank_id}")

    # Header
    st.header(f"⚠️ {translate('Failed Tests')} — {tank_name}")

    # Load failed tests
    df_failed = _load_failed_tests(tank_id)
    if df_failed.empty:
        st.info(translate("No out‑of‑range water tests for") + f" {tank_name}.")
        return

    # Prepare display DataFrame
    display_df = df_failed.copy()
    
    # Format temperature with units
    if "temperature" in display_df.columns:
        display_df["temperature"] = display_df["temperature"].apply(
            lambda v: format_with_units(v, "temp") if _pd.notnull(v) else "N/A"
        )
    # Format GH with units
    if "gh" in display_df.columns:
        display_df["gh"] = display_df["gh"].apply(
            lambda v: format_with_units(v, "hardness") if _pd.notnull(v) else "N/A"
        )

    # Localize and rename headers (override GH label)
    rename_map = {c: translate(c.capitalize()) for c in display_df.columns}
    if "gh" in rename_map:
        rename_map["gh"] = "GH (°dH)"
    display_df.rename(columns=rename_map, inplace=True)

    # Highlight out-of-range cells
    styled = highlight_out_of_range(display_df, SAFE_RANGES)

    # Display table
    if is_mobile():
        with st.expander(translate("Show Failed Tests"), expanded=False):
            st.dataframe(styled, use_container_width=True)
    else:
        st.dataframe(styled, use_container_width=True)
