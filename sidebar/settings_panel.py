# aquaLog/sidebar/settings_panel.py (Corrected)
"""
Settings panel (refactored, feature-complete).
"""

from __future__ import annotations
import sqlite3
from typing import Dict, Any, Tuple
import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from aqualog_db.repositories import (
    TankRepository,
    CustomRangeRepository,
    EmailSettingsRepository,
)
from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES
from utils import request_rerun


def render_settings_panel(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the entire settings sidebar panel."""
    tank_repo = TankRepository()
    custom_range_repo = CustomRangeRepository()
    email_repo = EmailSettingsRepository()

    render_add_tank_section(tank_repo, custom_range_repo)

    st.subheader("🔧 Edit Tank Settings")
    render_edit_tank_section(tank_map, tank_repo)
    render_custom_ranges_section(tank_map, custom_range_repo)

    tid = st.session_state.get("tank_id", 0)
    if tid:
        render_clear_tests_section(tid, tank_map)

    render_csv_import_section(tank_map)
    render_localization_section()
    render_weekly_email_section(tank_map, email_repo)


def render_add_tank_section(tank_repo: TankRepository, custom_range_repo: CustomRangeRepository) -> None:
    """➕ Add tank (with optional initial parameter ranges)."""
    st.subheader("➕ Add New Tank")

    name   = st.text_input("Name", key="new_tank_name")
    volume = st.number_input("Tank Volume (L)", min_value=0.0, step=0.1,
                             value=st.session_state.get("new_tank_volume", 0.0),
                             key="new_tank_volume")

    init_ranges = st.checkbox("Set initial parameter ranges", key="addtank_init_ranges")
    new_ranges: Dict[str, Tuple[float, float]] = {}

    if init_ranges:
        cols = st.columns(2)
        params_to_show = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
        for i, param in enumerate(params_to_show):
            low_default, high_default = SAFE_RANGES[param]
            col = cols[i % 2]
            low  = col.number_input(f"{param.capitalize()} safe low",  value=low_default,
                                    step=0.1, key=f"new_{param}_low")
            high = col.number_input(f"{param.capitalize()} safe high", value=high_default,
                                    step=0.1, key=f"new_{param}_high")
            new_ranges[param] = (low, high)

    if st.button("Add Tank", key="add_tank_btn"):
        if not name.strip():
            st.error("Tank name cannot be empty.")
        else:
            new_tank = tank_repo.add(name.strip(), volume or None)
            new_id = new_tank['id']
            for param, (low, high) in new_ranges.items():
                custom_range_repo.set(new_id, param, low, high)
            st.success(f"Added tank '{name.strip()}' ({volume} L)")
            request_rerun()


def render_edit_tank_section(tank_map: Dict[int, Dict[str, Any]], tank_repo: TankRepository) -> None:
    """✏️ Rename / Delete tank & edit volume for current tank."""
    st.subheader("✏️ Rename/Delete & Edit Volume")

    tid = st.session_state.get("tank_id", 0)
    if tid and tid in tank_map:
        current = tank_map[tid]
        new_name = st.text_input("New name", value=current["name"], key="rename_tank_field")
        new_vol  = st.number_input("Volume (L)", min_value=0.0, step=0.1,
                                   value=current.get("volume") or 0.0, key="edit_tank_volume")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", key="save_tank_changes_btn"):
                if new_name.strip() != current["name"]:
                    tank_repo.rename(tid, new_name.strip())
                if (current.get("volume") or 0) != new_vol:
                    tank_repo.update_volume(tid, new_vol)
                st.success(f"Updated tank to '{new_name.strip()}' ({new_vol} L)")
                request_rerun()
        with col2:
            if st.button("Delete This Tank", key="delete_tank_btn"):
                tank_repo.remove(tid)
                st.success(f"Deleted tank '{current['name']}'")
                request_rerun()
    else:
        st.info("Select a tank to edit.")


def render_custom_ranges_section(tank_map: Dict[int, Dict[str, Any]], custom_range_repo: CustomRangeRepository) -> None:
    """📊 Custom safe ranges for the current tank."""
    st.subheader("📊 Customize Parameter Ranges")

    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Select a tank to customize ranges.")
        return

    params = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
    sel_param = st.selectbox("Parameter", options=params, key="param_select")

    if sel_param:
        low_cur, high_cur = custom_range_repo.get(tid, sel_param) or SAFE_RANGES[sel_param]
        c1, c2 = st.columns(2)
        low_new  = c1.number_input("Safe Low",  value=low_cur,  step=0.1, key=f"low_{sel_param}")
        high_new = c2.number_input("Safe High", value=high_cur, step=0.1, key=f"high_{sel_param}")

        if st.button("Save Custom Range", key="save_custom_range_btn"):
            custom_range_repo.set(tid, sel_param, low_new, high_new)
            st.success(f"Custom range for {sel_param} saved")
            request_rerun()


def render_clear_tests_section(tid: int, tank_map: Dict[int, Dict[str, Any]]) -> None:
    """🗑️ Delete every water-test row for the current tank (with confirmation)."""
    st.subheader("⚠️ Clear Current Tank's Water Tests")

    prep_key = f"prepare_clear_tests_{tid}"
    confirm_ck = f"clear_confirm_checkbox_{tid}"
    yes_key = f"confirm_delete_tests_{tid}"
    cancel_key = f"cancel_clear_tests_{tid}"
    flag_key = f"clear_flag_{tid}"

    if not st.session_state.get(flag_key):
        if st.button("Prepare to clear tests", key=prep_key):
            st.session_state[flag_key] = True
            request_rerun()
    else:
        name = tank_map[tid]["name"]
        st.warning(f"🚨 Permanently delete **all** tests for '{name}'. This action **cannot** be undone.")
        confirm = st.checkbox(f"I understand and want to delete ALL tests for '{name}'", key=confirm_ck)
        
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if confirm and st.button("Yes, delete all", key=yes_key):
                with get_connection() as conn:
                    conn.execute("DELETE FROM water_tests WHERE tank_id = ?;", (tid,))
                    conn.commit()
                st.success(f"All tests for '{name}' deleted.")
                st.session_state.pop(flag_key, None)
                request_rerun()
        with col_cancel:
            if st.button("Cancel", key=cancel_key):
                st.session_state.pop(flag_key, None)
                st.info("Clear-tests operation cancelled.")
                request_rerun()


def render_csv_import_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """⬇️ Import CSV data into the current tank."""
    st.subheader("⬇️ Import from CSV")
    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Please select a tank before importing.")
        return

    uploaded = st.file_uploader("Choose CSV", type="csv", key="csv_uploader")
    if not uploaded:
        return

    if st.button("Import CSV", key="import_csv_btn"):
        try:
            df = pd.read_csv(uploaded)

            # FIXED: Added this line to clean/normalize the CSV column headers
            df.columns = df.columns.str.strip().str.lower()

            if 'id' in df.columns:
                df = df.drop(columns=['id'])

            if "date" not in df.columns:
                st.error("CSV must contain a 'date' column.")
                return
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
            df.dropna(subset=['date'], inplace=True)

            df["tank_id"] = tid

            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(water_tests);")
                db_columns = {row[1] for row in cursor.fetchall()}

            df_to_insert = df[[col for col in df.columns if col in db_columns]]

            with get_connection() as conn:
                df_to_insert.to_sql("water_tests", conn, if_exists="append", index=False)

            st.success(f"Imported {len(df_to_insert)} records into '{tank_map[tid]['name']}'")
            request_rerun()

        except Exception as e:
            st.error(f"Import failed: {e}")


def render_localization_section() -> None:
    """🌐 Choose language & unit system (stored in session)."""
    st.subheader("🌐 Localization & Units")
    st.selectbox("Language", list(LOCALIZATIONS.keys()), key="locale")
    st.selectbox("Units", list(UNIT_SYSTEMS.keys()), key="units")


def render_weekly_email_section(tank_map: Dict[int, Dict[str, Any]], email_repo: EmailSettingsRepository) -> None:
    """📧 Weekly summary email settings."""
    st.subheader("📧 Weekly Summary Email")

    settings = email_repo.get() or {}
    email = st.text_input("Email", value=settings.get("email", ""), key="email_addr")

    options  = list(tank_map.keys())
    
    try:
        default_tanks = settings.get("tanks", [])
    except:
        default_tanks = []

    selected = st.multiselect(
        "Tanks to include",
        options=options,
        default=[t for t in default_tanks if t in options],
        format_func=lambda tid: tank_map[tid]["name"],
        key="email_tanks",
    )

    st.markdown("**Include:**")
    inc_keys = [("include_type", "Maintenance type"), ("include_date", "Date"), ("include_notes", "Notes"), ("include_cost", "Cost"), ("include_stats", "Stats"), ("include_cycle", "Cycle status")]
    for key, label in inc_keys:
        st.checkbox(label, value=settings.get(key, False), key=key)

    if st.button("Save Email Settings", key="save_email_btn"):
        email_repo.save(
            email=email,
            tanks=selected,
            include_type=st.session_state["include_type"],
            include_date=st.session_state["include_date"],
            include_notes=st.session_state["include_notes"],
            include_cost=st.session_state["include_cost"],
            include_stats=st.session_state["include_stats"],
            include_cycle=st.session_state["include_cycle"],
        )
        st.success("Email settings saved")
        request_rerun()