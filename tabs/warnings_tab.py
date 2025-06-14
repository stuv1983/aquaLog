"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance

Displays structured warnings for the last 10 tests, including Seachem dosing advice
for low KH and GH based on tank volume.
"""
from __future__ import annotations
from typing import Any, List, Dict

import pandas as pd
import streamlit as st

# ——— Refactored DB imports ———
from aqualog_db.base   import BaseRepository

from aqualog_db.connection import get_connection
from aqualog_db.legacy import fetch_all_tanks

from config import SAFE_RANGES, ACTION_PLANS, CO2_COLOR_ADVICE
from utils import (
    translate,
    is_out_of_range,
    nh3_fraction,
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
)
from components import display_parameter_warning


def warnings_tab() -> None:
    tid = st.session_state.get("tank_id", 1)
    if not isinstance(tid, int) or tid == 0:
        st.warning("Please select a valid tank from the sidebar.")
        return

    # Build tank name and volume map
    tanks = fetch_all_tanks()
    tank_map: Dict[int, Dict[str, Any]] = {}
    for t in tanks:
        volume_raw = t.get("volume_l") or t.get("volume") or 0
        tank_map[t["id"]] = {
            "name": t.get("name", f"Tank #{t.get('id')}"),
            "volume": float(volume_raw) if volume_raw else None
        }

    tank_name = tank_map[tid]["name"]
    tank_vol = tank_map[tid]["volume"]

    st.header(f"⚠️ {translate('Warnings & Action Plan')} — {tank_name}")
    st.info("Displaying out-of-range warnings from the last 10 tests.")

    if tank_vol is None:
        st.info(
            "Tank volume not set; additional dosing calculations are unavailable."
            " Please set the tank volume (liters) in your tank settings."
        )

    # Fetch last 10 tests for this tank, excluding NULL dates
    with BaseRepository()._connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT *
              FROM water_tests
             WHERE tank_id = ?
               AND date IS NOT NULL
             ORDER BY date DESC
             LIMIT 10
            """,
            conn,
            params=(tid,),
            parse_dates=["date"],
        )

    # Drop any rows where parsing failed (NaT dates)
    df = df[df["date"].notna()]

    if df.empty:
        st.info(translate("No water tests logged yet."))
        return

    warnings_found = False
    for _, row in df.iterrows():
        ph, temp = row.get("ph"), row.get("temperature")
        breaches: List[str] = []

        # Identify which parameters are out of range
        for param, raw_val in row.items():
            if param in ("id", "tank_id", "date") or raw_val is None:
                continue
            if is_out_of_range(param, raw_val, tank_id=tid, ph=ph, temp_c=temp):
                breaches.append(param)

        if not breaches:
            continue

        warnings_found = True
        test_date_str = row["date"].strftime("%Y-%m-%d")
        breach_names = ", ".join(b.replace("_", " ").title() for b in breaches)

        with st.expander(f"⚠️ Test from {test_date_str} (Warnings for: {breach_names})"):
            for param in breaches:
                raw_val = row[param]

                # CO2 indicator special case
                if param == "co2_indicator":
                    colour = str(raw_val).capitalize()
                    advice = CO2_COLOR_ADVICE.get(colour)
                    if advice and colour != "Green":
                        st.warning(f"CO₂ Indicator: {colour}. {advice}")
                        st.markdown("---")
                    continue

                # Unionised ammonia
                if param == "ammonia" and ph is not None and temp is not None:
                    try:
                        ammonia_val = float(raw_val)
                        nh3_ppm = nh3_fraction(ammonia_val, ph, temp)
                        if nh3_ppm > SAFE_RANGES["ammonia"][1]:
                            st.error("High unionised ammonia (NH₃) detected")
                            st.metric(
                                label="Calculated Toxic NH₃",
                                value=f"{nh3_ppm:.3f} ppm",
                                delta="Target: < 0.02 ppm",
                                delta_color="inverse"
                            )
                            st.markdown("**Recommended Actions:**")
                            for step in ACTION_PLANS["ammonia"]:
                                st.write(f"- {step}")
                            st.markdown("---")
                    except (ValueError, TypeError):
                        pass
                    continue

                # Standard numeric parameter warning
                try:
                    val = float(raw_val)
                except (ValueError, TypeError):
                    continue

                safe_lo, safe_hi = SAFE_RANGES.get(param, (None, None))
                is_low = safe_lo is not None and val < safe_lo

                display_parameter_warning(param, val, (safe_lo, safe_hi), is_low)

                # Additional dosing advice for low KH/GH
                if is_low and tank_vol:
                    delta = safe_lo - val
                    if param == "kh":
                        dose_g = calculate_alkaline_buffer_dose(tank_vol, delta)
                        tsp = dose_g / 6
                        st.markdown("**Additional Dosing Advice:**")
                        st.info(f"To raise KH by {delta:.1f}°dKH in your {tank_vol:.1f} L tank:")
                        st.warning(f"➡️ Add approx. **{dose_g:.1f} g** (or **{tsp:.2f} tsp**) of **Seachem Alkaline Buffer**.")
                    elif param == "gh":
                        dose_g = calculate_equilibrium_dose(tank_vol, delta)
                        tbs = dose_g / 16
                        st.markdown("**Additional Dosing Advice:**")
                        st.info(f"To raise GH by {delta:.1f}°dGH in your {tank_vol:.1f} L tank:")
                        st.warning(f"➡️ Add approx. **{dose_g:.1f} g** (or **{tbs:.2f} tbsp**) of **Seachem Equilibrium**.")
                    st.markdown("---")
    if not warnings_found:
        st.success("✅ No warnings found in the last 10 tests. All parameters are within safe ranges.")

# Alias for loader
warnings_tab = warnings_tab
