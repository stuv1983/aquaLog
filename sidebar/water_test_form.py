import streamlit as st
from datetime import datetime
from typing import Dict, Any
from db import save_water_test
from utils import show_toast, show_out_of_range_banner

def render_water_test_form(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the water test logging form."""
    st.sidebar.header("🔬 Log Water Test")

    # Main parameters
    ph = st.sidebar.number_input(
        "pH", min_value=0.0, step=0.1, value=st.session_state.get("ph", 7.6), key="ph"
    )
    ammonia = st.sidebar.number_input(
        "Ammonia (ppm)", min_value=0.0, step=0.01, value=st.session_state.get("ammonia", 0.0), key="ammonia"
    )
    nitrite = st.sidebar.number_input(
        "Nitrite (ppm)", min_value=0.0, step=0.01, value=st.session_state.get("nitrite", 0.0), key="nitrite"
    )
    nitrate = st.sidebar.number_input(
        "Nitrate (ppm)", min_value=0.0, step=0.1, value=st.session_state.get("nitrate", 0.0), format="%.1f", key="nitrate"
    )

    st.sidebar.markdown("---")

    kh_drops = st.sidebar.number_input(
        "KH Test Drops", min_value=0, step=1,
        value=st.session_state.get("kh_drops", 4),
        help="Enter drop count from your liquid test kit. 1 drop = 1 dKH.",
        key="kh_drops"
    )
    gh_drops = st.sidebar.number_input(
        "GH Test Drops", min_value=0, step=1,
        value=st.session_state.get("gh_drops", 8),
        help="Enter drop count from your liquid test kit. 1 drop = 1 dGH.",
        key="gh_drops"
    )
    kh = float(kh_drops)
    gh = float(gh_drops)
    kh_ppm = kh * 17.86
    gh_ppm = gh * 17.86
    st.sidebar.markdown(f"**KH:** {kh_ppm:.1f} ppm | **GH:** {gh_ppm:.1f} ppm")

    st.sidebar.markdown("---")

    co2_color = st.sidebar.selectbox(
        "CO₂ Indicator",
        ["Green", "Blue", "Yellow"],
        index=["Green", "Blue", "Yellow"].index(
            st.session_state.get("co2_color", "Green")
        ),
        key="co2_color"
    )
    temperature = st.sidebar.number_input(
        "Temperature (°C)", min_value=0.0, step=0.5,
        value=st.session_state.get("temperature", 26.0),
        key="temperature"
    )
    notes = st.sidebar.text_area(
        "Notes (optional)",
        value=st.session_state.get("notes", ""),
        key="notes"
    )

    if st.sidebar.button("💾 Save Test"):
        if st.session_state.get("tank_id", 0) != 0:
            data = {
                "date": datetime.now().isoformat(),
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
                save_water_test(data, st.session_state["tank_id"])
                st.sidebar.success("Water test saved!")
                show_toast()
                show_out_of_range_banner()
            except Exception as e:
                st.sidebar.error(f"Failed to save test: {e}")
        else:
            st.sidebar.error("Please add and select a tank before saving a test.")
