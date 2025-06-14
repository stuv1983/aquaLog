import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple

from db import get_connection
from utils import request_rerun

from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES
from utils import request_rerun
from db import (
    add_tank, rename_tank, remove_tank, update_tank_volume,
    set_custom_range, get_custom_range, get_connection,
    get_user_email_settings, save_user_email_settings
)
# from .clear_tests import render_clear_tests_section

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

def render_add_tank_section() -> None:
    """➕ Add New Tank with optional initial ranges."""
    st.subheader("➕ Add New Tank")
    name = st.text_input("Name", key="new_tank_name")
    volume = st.number_input(
        "Tank Volume (L)", min_value=0.0, step=0.1,
        value=st.session_state.get("new_tank_volume", 0.0),
        key="new_tank_volume"
    )
    init_ranges = st.checkbox("Set initial parameter ranges", key="init_ranges_checkbox")
    new_ranges: Dict[str, Tuple[float, float]] = {}
    if init_ranges:
        cols = st.columns(2)
        params = [p for p in SAFE_RANGES.keys() if p not in ("co2_indicator", "ammonia")]
        for i, param in enumerate(params):
            default_low, default_high = SAFE_RANGES[param]
            col = cols[i % 2]
            low = col.number_input(
                f"{param.capitalize()} safe low", value=default_low, step=0.1,
                key=f"new_{param}_low"
            )
            high = col.number_input(
                f"{param.capitalize()} safe high", value=default_high, step=0.1,
                key=f"new_{param}_high"
            )
            new_ranges[param] = (low, high)
    if st.button("Add Tank", key="add_tank_btn"):
        if not name.strip():
            st.error("Tank name cannot be empty.")
        else:
            new_id = add_tank(name.strip(), volume)
            for param, (low, high) in new_ranges.items():
                set_custom_range(new_id, param, low, high)
            st.success(f"Added tank '{name.strip()}' ({volume} L)")
            request_rerun()

def render_edit_tank_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """✏️ Rename/Delete & Edit Volume for current tank."""
    st.subheader("✏️ Rename/Delete & Edit Volume")
    tid = st.session_state.get("tank_id", 0)
    if tid and tid in tank_map:
        current = tank_map[tid]
        new_name = st.text_input("New name", value=current["name"], key="rename_tank_field")
        new_vol = st.number_input(
            "Volume (L)", min_value=0.0, step=0.1,
            value=current["volume"], key="edit_tank_volume"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", key="save_tank_changes_btn"):
                if new_name.strip() != current["name"]:
                    rename_tank(tid, new_name.strip())
                if new_vol != current["volume"]:
                    update_tank_volume(tid, new_vol)
                st.success(f"Updated tank to '{new_name.strip()}' ({new_vol} L)")
                request_rerun()
        with col2:
            if st.button("Delete This Tank", key="delete_tank_btn"):
                remove_tank(tid)
                st.success(f"Deleted tank '{current['name']}'")
                request_rerun()
    else:
        st.info("Select a tank to edit.")

def render_custom_ranges_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """📊 Customize Parameter Ranges for current tank."""
    st.subheader("📊 Customize Parameter Ranges")
    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Select a tank to customize ranges.")
        return
    params = [p for p in SAFE_RANGES.keys() if p not in ("co2_indicator", "ammonia")]
    sel = st.selectbox("Select parameter", options=params, key="param_select")
    if sel:
        low_cur, high_cur = get_custom_range(tid, sel) or SAFE_RANGES[sel]
        c1, c2 = st.columns(2)
        low_new = c1.number_input("Safe Low", value=low_cur, step=0.1, key=f"low_{sel}")
        high_new = c2.number_input("Safe High", value=high_cur, step=0.1, key=f"high_{sel}")
        if st.button("Save Custom Range", key="save_custom_range_btn"):
            set_custom_range(tid, sel, low_new, high_new)
            st.success(f"Custom range for {sel} saved!")
            request_rerun()

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
                    with get_connection() as conn:
                        df.to_sql("water_tests", conn, if_exists="append", index=False)
                    st.success(f"Imported {len(df)} records into tank '{tank_map[tid]['name']}'")
                    request_rerun()
            except Exception as e:
                st.error(f"Import error: {e}")

# In settings_panel.py, add this function (remove the import of clear_tests):

def render_clear_tests_section(tid: int, tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the clear tests section with unique keys."""
    st.subheader("⚠️ Clear Current Tank's Water Tests")

    flag_key = f"confirm_clear_current_{tid}_flag"
    prep_key = f"prepare_clear_tests_{tid}_button"
    checkbox_key = f"clear_confirm_checkbox_{tid}_input"
    yes_key = f"confirm_delete_tests_{tid}_button"
    cancel_key = f"cancel_clear_tests_{tid}_button"

    if not st.session_state.get(flag_key, False):
        if st.button("Prepare to clear this tank's tests", key=prep_key):
            st.session_state[flag_key] = True
            request_rerun()
    else:
        name = tank_map.get(tid, {}).get("name", "this tank")
        st.warning(
            f"🚨 Permanently delete **all** tests for '{name}'.\n"
            f"This action **cannot** be undone."
        )
        confirm = st.checkbox(
            f"I understand and want to delete ALL tests for '{name}'",
            key=checkbox_key
        )
        if confirm and st.button("Yes, delete all tests", key=yes_key):
            try:
                with get_connection() as conn:
                    conn.execute(
                        "DELETE FROM water_tests WHERE tank_id = ?;",
                        (tid,)
                    )
                st.success(f"All tests for '{name}' have been deleted.")
            except Exception as e:
                st.error(f"Error deleting tests: {e}")
            finally:
                st.session_state.pop(flag_key, None)
                request_rerun()
        if st.button("Cancel", key=cancel_key):
            st.session_state.pop(flag_key, None)
            st.info("Clear-tests operation cancelled.")
            request_rerun()

def render_localization_section() -> None:
    """🌐 Localization & Units settings."""
    st.subheader("🌐 Localization & Units")
    st.selectbox("Language", list(LOCALIZATIONS.keys()), key="locale")
    st.selectbox("Units", list(UNIT_SYSTEMS.keys()), key="units")

def render_weekly_email_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """📧 Weekly Summary Email configuration."""
    st.subheader("📧 Weekly Summary Email")
    settings = get_user_email_settings() or {}
    email = st.text_input("Email", value=settings.get("email", ""), key="email_address")
    options = list(tank_map.keys())
    default = settings.get("tanks", [])
    invalid = set(default) - set(options)
    if invalid:
        st.warning(f"Removed invalid tank IDs: {', '.join(map(str, invalid))}")
    selected = st.multiselect(
        "Tanks", options=options, default=[t for t in default if t in options],
        format_func=lambda t: tank_map[t]["name"], key="email_tanks"
    )
    st.markdown("**Include:**")
    for key, label in [("include_type","Type"),("include_date","Date"),
                       ("include_notes","Notes"),("include_cost","Cost"),
                       ("include_stats","Stats"),("include_cycle","Cycle")]:
        st.checkbox(label, value=settings.get(key, False), key=key)
    if st.button("Save Email Settings", key="save_email_btn"):
        save_user_email_settings(
            email=st.session_state["email_address"],
            tanks=st.session_state["email_tanks"],
            include_type=st.session_state["include_type"],
            include_date=st.session_state["include_date"],
            include_notes=st.session_state["include_notes"],
            include_cost=st.session_state["include_cost"],
            include_stats=st.session_state["include_stats"],
            include_cycle=st.session_state["include_cycle"],
        )
        st.success("Email settings saved")
        request_rerun()
