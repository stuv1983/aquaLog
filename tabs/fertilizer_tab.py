# tabs/fertilizer_tab.py
# "Fertilizer Schedule & Log" tab: calculates recommended fertilizer dosage based on nitrate

import pandas as pd
import streamlit as st

# Utility functions:
#   - is_mobile: detect if user is on mobile viewport for responsive layout
#   - show_out_of_range_banner: display any persistent warnings if latest test had out‐of‐range values
#   - get_latest_test: retrieve the most recent water test record as a dict
from utils import is_mobile, show_out_of_range_banner, get_latest_test
# Configuration constants:
#   - SAFE_RANGES: dict mapping each parameter to (min, max) safe values
#   - DEFAULT_TANK_VOLUME: default volume (L) used if user does not specify
from config import SAFE_RANGES, DEFAULT_TANK_VOLUME


def fertilizer_tab() -> None:
    """
    Render the "Fertilizer Schedule & Log" tab, which:
      1. Displays a header and any out‐of‐range banner from the latest test.
      2. Retrieves the most recent nitrate reading.
      3. Prompts the user for tank volume (L), defaulting to DEFAULT_TANK_VOLUME.
      4. Calculates target nitrate (midpoint of safe range), computes delta (how much to raise),
         and recommends a dose of "Leaf One" fertilizer in mL.
      5. Shows result: either "No fertilizer needed" if nitrate ≥ target,
         or the calculated dosage if below target.

    Dose calculation logic:
      • target = (safe_low + safe_high) / 2
      • delta = max(0, target - latest_nitrate)
      • dose_ml = round((delta / 10) * (tank_volume_L / 100) * 5, 1)
        Explanation: Leaf One raises NO₃ by 10 ppm per 5 mL in 100 L of water.  
                    Therefore, to raise by delta ppm in `vol` L:  
                      dose_ml = (delta ppm / 10 ppm) * (vol / 100 L) * 5 mL
    """
    # 1) Header and warning banner
    st.header("💊 Fertilizer Schedule & Log")
    # Show persistent out‐of‐range banner if the latest test has issues
    #show_out_of_range_banner("fertilizer")

    # 2) Retrieve the latest water test record
    latest = get_latest_test()
    if latest is None:
        # No tests logged yet → inform user and exit
        st.info("No water tests logged yet.")
        return

    # 3) Extract the most recent nitrate reading
    nitr = latest.get("nitrate")
    # If nitrate is None or NaN, inform user there is no value to base calculation on
    if nitr is None or not pd.notna(nitr):
        st.info("No nitrate reading available in the latest test.")
        return

    # 4) Prompt user for tank volume (L)
    #    Use different Streamlit keys for mobile vs. desktop to keep session state separate
    if is_mobile():
        vol = st.number_input(
            "Tank volume (L)",
            min_value=1,
            value=DEFAULT_TANK_VOLUME,
            step=1,
            help="Enter your tank’s volume in Litres.",
            key="fert_vol_mobile",
        )
    else:
        vol = st.number_input(
            "Tank volume (L)",
            min_value=1,
            value=DEFAULT_TANK_VOLUME,
            step=1,
            help="Enter your tank’s volume in Litres.",
            key="fert_vol"
        )

    # 5) Compute target nitrate as midpoint of safe range
    lo, hi = SAFE_RANGES["nitrate"]
    target = (lo + hi) / 2
    # Delta = how many ppm needed to reach target; do not go below zero
    delta = max(0, target - nitr)
    # Dose calculation:
    #   Leaf One raises NO₃ by 10 ppm per 5 mL in 100 L.
    #   => (delta / 10) = fraction of 5 mL for 100 L
    #   => multiply by (vol / 100) to scale from 100 L to `vol` L
    #   => multiply by 5 mL to get final dosage
    dose_ml = round((delta / 10) * (vol / 100) * 5, 1)

    # 6) Display summary of last NO₃, target, and recommendation
    st.write(f"**Last NO₃:** {nitr:.1f} ppm → **Target:** {target:.1f} ppm")
    if delta <= 0:
        # If delta ≤ 0, nitrate is at or above target → no fertilizer needed
        st.success("No fertilizer needed—nitrate is at or above target.")
    else:
        # Otherwise, show how many mL of Leaf One to add to raise by delta
        st.write(
            f"Add approximately **{dose_ml:.1f} mL** of Leaf One to raise NO₃ by {delta:.1f} ppm."
        )
