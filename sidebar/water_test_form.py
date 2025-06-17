# sidebar/water_test_form.py (Fully Updated)
"""
Sidebar - Water-test logging form (multi-tank aware)
Renders a multi-step "wizard" form on mobile and a standard form on desktop.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import streamlit as st

from aqualog_db.repositories import WaterTestRepository
from utils import (
    show_toast,
    show_out_of_range_banner,
    arrow_safe,
    is_mobile,
)

def render_water_test_form(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the water-test logging form in the sidebar."""
    st.sidebar.header("🔬 Log Water Test")

    # =====================================================================
    #  MOBILE WIZARD (Multi-Step Form)
    # =====================================================================
    if is_mobile():
        # Initialize session state for the form wizard
        if 'form_step' not in st.session_state:
            st.session_state.form_step = 1

        # --- STEP 1: Main Parameters ---
        if st.session_state.form_step == 1:
            with st.sidebar.form("step1_form"):
                st.caption("Step 1 of 3: Main Parameters")
                ph = st.number_input("pH", min_value=0.0, step=0.1, value=st.session_state.get("ph_val", 7.6))
                ammonia = st.number_input("Ammonia (ppm)", min_value=0.0, step=0.01, value=st.session_state.get("ammonia_val", 0.0))
                nitrite = st.number_input("Nitrite (ppm)", min_value=0.0, step=0.01, value=st.session_state.get("nitrite_val", 0.0))
                nitrate = st.number_input("Nitrate (ppm)", min_value=0.0, step=0.1, value=st.session_state.get("nitrate_val", 0.0), format="%.1f")
                
                if st.form_submit_button("Next →", use_container_width=True):
                    st.session_state.ph_val = ph
                    st.session_state.ammonia_val = ammonia
                    st.session_state.nitrite_val = nitrite
                    st.session_state.nitrate_val = nitrate
                    st.session_state.form_step = 2
                    st.rerun()

        # --- STEP 2: Hardness & Temperature ---
        elif st.session_state.form_step == 2:
            with st.sidebar.form("step2_form"):
                st.caption("Step 2 of 3: Hardness & Temp")
                kh_drops = st.number_input("KH Test Drops", min_value=0, step=1, value=st.session_state.get("kh_drops_val", 4))
                gh_drops = st.number_input("GH Test Drops", min_value=0, step=1, value=st.session_state.get("gh_drops_val", 8))
                temperature = st.number_input("Temperature (°C)", min_value=0.0, step=0.5, value=st.session_state.get("temp_val", 26.0))

                c1, c2 = st.columns(2)
                if c1.form_submit_button("← Back", use_container_width=True):
                    st.session_state.form_step = 1
                    st.rerun()
                if c2.form_submit_button("Next →", use_container_width=True):
                    st.session_state.kh_drops_val = kh_drops
                    st.session_state.gh_drops_val = gh_drops
                    st.session_state.temp_val = temperature
                    st.session_state.form_step = 3
                    st.rerun()

        # --- STEP 3: Final Details & Save ---
        elif st.session_state.form_step == 3:
            with st.sidebar.form("step3_form"):
                st.caption("Step 3 of 3: Final Details")
                co2_color = st.selectbox("CO₂ Indicator", ["Green", "Blue", "Yellow"], index=0)
                notes = st.text_area("Notes (optional)", "")

                c1, c2 = st.columns(2)
                if c1.form_submit_button("← Back", use_container_width=True):
                    st.session_state.form_step = 2
                    st.rerun()

                if c2.form_submit_button("💾 Save Test", type="primary", use_container_width=True):
                    tank_id = st.session_state.get("tank_id", 0)
                    if tank_id == 0:
                        st.sidebar.error("Select a tank first.")
                    else:
                        data = {
                            "date": datetime.now().isoformat(timespec="seconds"),
                            "ph": st.session_state.ph_val,
                            "ammonia": st.session_state.ammonia_val,
                            "nitrite": st.session_state.nitrite_val,
                            "nitrate": st.session_state.nitrate_val,
                            "kh": float(st.session_state.kh_drops_val),
                            "gh": float(st.session_state.gh_drops_val),
                            "co2_indicator": co2_color,
                            "temperature": st.session_state.temp_val,
                            "notes": notes,
                        }
                        try:
                            repo = WaterTestRepository()
                            repo.save(data, tank_id)
                            st.sidebar.success("Water test saved!")
                            # Clean up session state
                            for key in ['form_step', 'ph_val', 'ammonia_val', 'nitrite_val', 'nitrate_val', 'kh_drops_val', 'gh_drops_val', 'temp_val']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.rerun()
                        except Exception as exc:
                            st.sidebar.error(f"Failed to save test: {exc}")
    
    # =====================================================================
    # DESKTOP VERSION (Original Single Form)
    # =====================================================================
    else:
        with st.sidebar.form("desktop_form"):
            ph = st.number_input("pH", min_value=0.0, step=0.1, value=7.6)
            ammonia = st.number_input("Ammonia (ppm)", min_value=0.0, step=0.01, value=0.0)
            nitrite = st.number_input("Nitrite (ppm)", min_value=0.0, step=0.01, value=0.0)
            nitrate = st.number_input("Nitrate (ppm)", min_value=0.0, step=0.1, value=0.0, format="%.1f")
            st.markdown("---")
            kh_drops = st.number_input("KH Test Drops", min_value=0, step=1, value=4)
            gh_drops = st.number_input("GH Test Drops", min_value=0, step=1, value=8)
            st.markdown("---")
            co2_color = st.selectbox("CO₂ Indicator", ["Green", "Blue", "Yellow"], index=0)
            temperature = st.number_input("Temperature (°C)", min_value=0.0, step=0.5, value=26.0)
            notes = st.text_area("Notes (optional)", "")
            
            if st.form_submit_button("💾 Save Test"):
                tank_id = st.session_state.get("tank_id", 0)
                if tank_id == 0:
                    st.error("Please add and select a tank before saving a test.")
                else:
                    data = {
                        "date": datetime.now().isoformat(timespec="seconds"),
                        "ph": ph, "ammonia": ammonia, "nitrite": nitrite, "nitrate": nitrate,
                        "kh": float(kh_drops), "gh": float(gh_drops), "co2_indicator": co2_color,
                        "temperature": temperature, "notes": notes,
                    }
                    try:
                        repo = WaterTestRepository()
                        repo.save(data, tank_id)
                        st.sidebar.success("Water test saved!")
                        show_toast("Test Saved", "Your readings were successfully recorded.")
                        # Do not rerun here to allow success message to be seen
                    except Exception as exc:
                        st.sidebar.error(f"Failed to save test: {exc}")