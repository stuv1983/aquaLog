import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple

from aqualog_db.base import BaseRepository
from utils import request_rerun

from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES
from aqualog_db.legacy import (
    add_tank,
    rename_tank,
    remove_tank,
    update_tank_volume,
    set_custom_range,
    get_custom_range,
    get_user_email_settings,
    save_user_email_settings,
)

def render_settings_panel(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the full settings panel with all subsections."""
    with st.sidebar.expander("⚙️ Settings", expanded=False):
        # Add New Tank
        render_add_tank_section()

        # Group edit-related settings
        st.subheader("🔧 Edit Tank Settings")
        render_edit_tank_section(tank_map)
        render_custom_ranges_section(tank_map)
        # Clear tests for the selected tank
        tid = st.session_state.get("tank_id", 0)
        if tid:
            render_clear_tests_section(tid, tank_map)

        # Import from CSV
        render_csv_import_section(tank_map)

        # Localization & Units
        render_localization_section()

        # Weekly Summary Email
        render_weekly_email_section(tank_map)

# Definitions for the subsections...

def render_csv_import_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """⬇️ Import Water Tests from CSV for current tank."""
    st.subheader("⬇️ Import from CSV")
    tid = st.session_state.get("tank_id", 0)
    uploaded = st.file_uploader("Upload CSV", type="csv", key="csv_uploader")
    if st.button("Import from CSV", key="import_csv_btn"):
        if not uploaded:
            st.warning("Please upload a CSV first.")
        else:
            try:
                df = pd.read_csv(uploaded)
                expected = [
                    "date", "ph", "ammonia", "nitrite", "nitrate",
                    "kh", "gh", "co2_indicator", "temperature", "notes"
                ]
                missing = [c for c in expected if c not in df.columns]
                if missing:
                    st.error(f"Missing columns: {', '.join(missing)}")
                else:
                    df["tank_id"] = tid
                    # Use BaseRepository for connection
                    with BaseRepository()._connection() as conn:
                        df.to_sql("water_tests", conn, if_exists="append", index=False)
                    st.success(
                        f"Imported {len(df)} records into tank '{tank_map[tid]['name']}'"
                    )
                    request_rerun()
            except Exception as e:
                st.error(f"Import error: {e}")
