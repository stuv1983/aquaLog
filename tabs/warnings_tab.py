"""
tabs/warnings_tab.py – collapsible, structured warnings with dosing guidance
(Arrow-safe & legacy-compatible)

Differences from the previous revision
──────────────────────────────────────
• Before sending a parameter to `display_parameter_warning` we now make sure
  it is in the widget’s own “allowed” list.  Anything else is silently skipped,
  so the “Invalid parameter” exception cannot fire.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from aqualog_db.legacy     import fetch_all_tanks

from config import SAFE_RANGES, ACTION_PLANS, CO2_COLOR_ADVICE
from utils import (
    translate,
    arrow_safe,
    is_out_of_range,
    nh3_fraction,
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
)
from components import display_parameter_warning

print(">>> LOADING", __file__)

# Widget accepts exactly these keys (from its source).
_ALLOWED_FOR_WIDGET = {
    "ammonia", "gh", "kh", "nitrate", "nitrite", "ph", "temperature"
}


def warnings_tab() -> None:
    tid: int = st.session_state.get("tank_id", 1)
    if not isinstance(tid, int) or tid == 0:
        st.warning("Please select a valid tank from the sidebar.")
        return

    tanks = fetch_all_tanks()
    tank_map: Dict[int, Dict[str, Any]] = {
        t["id"]: {
            "name":   t.get("name", f"Tank #{t['id']}"),
            "volume": float(t.get("volume_l") or t.get("volume") or 0) or None,
        }
        for t in tanks
    }

    tank_name = tank_map[tid]["name"]
    tank_vol  = tank_map[tid]["volume"]

    st.header(f"⚠️ {translate('Warnings & Action Plan')} — {tank_name}")
    st.info("Showing out-of-range warnings from the last **10** tests.")

    if tank_vol is None:
        st.info(
            "Tank volume not set; dosing calculations unavailable. "
            "Set the volume (litres) in **Settings → Edit Tank**."
        )

    # ── Pull last 10 tests ────────────────────────────────────────────────
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT *
              FROM water_tests
             WHERE tank_id = ?
               AND date IS NOT NULL
             ORDER BY date DESC
             LIMIT 10;
            """,
            conn,
            params=(tid,),
            parse_dates=["date"],
        )

    df = df[df["date"].notna()]
    if df.empty:
        st.info(translate("No water tests logged yet."))
        return

    warnings_found = False

    for _, row in df.iterrows():
        ph   = row.get("ph")
        temp = row.get("temperature")
        breaches: List[str] = []

        # ── Find breaches ─────────────────────────────────────────────────
        for param, raw_val in row.items():
            if param in ("id", "tank_id", "date") or raw_val is None:
                continue

            cond = is_out_of_range(param, raw_val, tank_id=tid, ph=ph, temp_c=temp)
            if isinstance(cond, pd.Series):
                cond = cond.any()
            else:
                try:
                    cond = bool(cond)
                except Exception:
                    cond = False

            if cond:
                breaches.append(param)

        if not breaches:
            continue

        warnings_found = True
        dt_label  = row["date"].strftime("%Y-%m-%d")
        bad_label = ", ".join(b.replace("_", " ").title() for b in breaches)

        with st.expander(f"⚠️ Test {dt_label} — {bad_label}"):
            for param in breaches:
                raw_val = row[param]

                # CO₂ colour
                if param == "co2_indicator":
                    colour = str(raw_val).capitalize()
                    advice = CO2_COLOR_ADVICE.get(colour)
                    if advice and colour != "Green":
                        st.warning(f"CO₂ Indicator: {colour}. {advice}")
                        st.markdown("---")
                    continue

                # Ammonia → toxic NH₃
                if param == "ammonia" and ph is not None and temp is not None:
                    try:
                        nh3_ppm = nh3_fraction(float(raw_val), ph, temp)
                        if nh3_ppm > SAFE_RANGES["ammonia"][1]:
                            st.error("High unionised ammonia (NH₃) detected")
                            st.metric(
                                label="Calculated Toxic NH₃",
                                value=f"{nh3_ppm:.3f} ppm",
                                delta="Target < 0.02 ppm",
                                delta_color="inverse",
                            )
                            st.markdown("**Recommended Actions:**")
                            for step in ACTION_PLANS["ammonia"]:
                                st.write(f"- {step}")
                            st.markdown("---")
                    except Exception:
                        pass
                    continue

                # Only feed the widget the params it accepts
                if param not in _ALLOWED_FOR_WIDGET:
                    continue

                try:
                    val = float(raw_val)
                except Exception:
                    continue

                safe_lo, safe_hi = SAFE_RANGES.get(param, (None, None))
                is_low = safe_lo is not None and val < safe_lo

                display_parameter_warning(param, val, (safe_lo, safe_hi), is_low)

                if is_low and tank_vol:
                    delta = safe_lo - val
                    if param == "kh":
                        dose_g = calculate_alkaline_buffer_dose(tank_vol, delta)
                        tsp    = dose_g / 6
                        st.markdown("**Additional Dosing Advice:**")
                        st.info(f"Raise KH by {delta:.1f} °dKH in {tank_vol:.1f} L:")
                        st.warning(f"➡️ Add ≈ **{dose_g:.1f} g** (~**{tsp:.2f} tsp**) Alkaline Buffer.")
                    elif param == "gh":
                        dose_g = calculate_equilibrium_dose(tank_vol, delta)
                        tbsp   = dose_g / 16
                        st.markdown("**Additional Dosing Advice:**")
                        st.info(f"Raise GH by {delta:.1f} °dGH in {tank_vol:.1f} L:")
                        st.warning(f"➡️ Add ≈ **{dose_g:.1f} g** (~**{tbsp:.2f} tbsp**) Equilibrium.")
                    st.markdown("---")

    if not warnings_found:
        st.success("✅ No warnings found in the last 10 tests — all parameters within safe range.")


# Alias for dynamic loader
warnings_tab = warnings_tab
