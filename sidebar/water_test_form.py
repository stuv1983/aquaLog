"""
Sidebar - Water-test logging form (multi-tank aware)
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

import pandas as pd
import streamlit as st

from aqualog_db.legacy import save_water_test
from utils import (
    show_toast,
    show_out_of_range_banner,
    arrow_safe,
)

def render_water_test_form(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the water-test logging form in the sidebar."""
    st.sidebar.header("🔬 Log Water Test")

    # ── Main parameters ────────────────────────────────────────────────────
    ph = st.sidebar.number_input(
        "pH", min_value=0.0, step=0.1,
        value=st.session_state.get("ph", 7.6), key="ph"
    )
    ammonia = st.sidebar.number_input(
        "Ammonia (ppm)", min_value=0.0, step=0.01,
        value=st.session_state.get("ammonia", 0.0), key="ammonia"
    )
    nitrite = st.sidebar.number_input(
        "Nitrite (ppm)", min_value=0.0, step=0.01,
        value=st.session_state.get("nitrite", 0.0), key="nitrite"
    )
    nitrate = st.sidebar.number_input(
        "Nitrate (ppm)", min_value=0.0, step=0.1,
        value=st.session_state.get("nitrate", 0.0), format="%.1f", key="nitrate"
    )

    st.sidebar.markdown("---")

    # ── KH / GH drops ──────────────────────────────────────────────────────
    kh_drops = st.sidebar.number_input(
        "KH Test Drops", min_value=0, step=1,
        value=st.session_state.get("kh_drops", 4),
        help="Liquid-kit drops (1 drop = 1 dKH).",
        key="kh_drops",
    )
    gh_drops = st.sidebar.number_input(
        "GH Test Drops", min_value=0, step=1,
        value=st.session_state.get("gh_drops", 8),
        help="Liquid-kit drops (1 drop = 1 dGH).",
        key="gh_drops",
    )
    kh, gh = float(kh_drops), float(gh_drops)
    st.sidebar.markdown(f"**KH:** {kh * 17.86:.1f} ppm &nbsp;|&nbsp; **GH:** {gh * 17.86:.1f} ppm")

    st.sidebar.markdown("---")

    # ── Other fields ───────────────────────────────────────────────────────
    co2_color = st.sidebar.selectbox(
        "CO₂ Indicator", ["Green", "Blue", "Yellow"],
        index=["Green", "Blue", "Yellow"].index(st.session_state.get("co2_color", "Green")),
        key="co2_color",
    )
    temperature = st.sidebar.number_input(
        "Temperature (°C)", min_value=0.0, step=0.5,
        value=st.session_state.get("temperature", 26.0), key="temperature"
    )
    notes = st.sidebar.text_area(
        "Notes (optional)", value=st.session_state.get("notes", ""), key="notes"
    )

    # ── Save button ────────────────────────────────────────────────────────
    if st.sidebar.button("💾 Save Test"):
        tank_id = st.session_state.get("tank_id", 0)
        if tank_id == 0:
            st.sidebar.error("Please add and select a tank before saving a test.")
            return

        data = {
            "date": datetime.now().isoformat(timespec="seconds"),
            "ph": ph,
            "ammonia": ammonia,
            "nitrite": nitrite,
            "nitrate": nitrate,
            "kh": kh,
            "gh": gh,
            "co2_indicator": co2_color,
            "temperature": temperature,
            "notes": notes,
        }

        try:
            save_water_test(data, tank_id)
            st.sidebar.success("Water test saved!")

            preview_df = pd.DataFrame([data])
            st.sidebar.dataframe(arrow_safe(preview_df), use_container_width=True)

            # FIX: Added the required 'title' and 'message' arguments.
            show_toast("Test Saved", "Your readings were successfully recorded.")
            
            show_out_of_range_banner()
        except Exception as exc:
            st.sidebar.error(f"Failed to save test: {exc}")