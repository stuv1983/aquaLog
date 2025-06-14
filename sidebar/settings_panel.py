# aquaLog/sidebar/settings_panel.py
"""
Settings panel (refactored, feature-complete).

Features
────────
● ➕  Add new tank (with optional initial safe-ranges)
● ✏️  Rename / Delete tank & edit volume
● 📊  Custom parameter ranges per tank
● 🗑️  Clear all tests for current tank
● ⬇️  CSV import for current tank
● 🌐  Localisation & unit preferences
● 📧  Weekly summary email configuration
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, Any, Tuple, List

import pandas as pd
import streamlit as st

# ─── DB helpers ──────────────────────────────────────────────────────────────
from aqualog_db.connection import get_connection
from aqualog_db.legacy import (
    add_tank,
    rename_tank,
    remove_tank,
    update_tank_volume,
    set_custom_range,
    get_custom_range,
    get_user_email_settings,
    save_user_email_settings,
    fetch_all_tanks,
)

# ─── App-level config & utils ────────────────────────────────────────────────
from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES
from utils  import request_rerun


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
def render_settings_panel(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """Render the entire settings sidebar panel."""
    with st.sidebar.expander("⚙️ Settings", expanded=False):
        render_add_tank_section()

        st.subheader("🔧 Edit Tank Settings")
        render_edit_tank_section(tank_map)
        render_custom_ranges_section(tank_map)

        tid = st.session_state.get("tank_id", 0)
        if tid:
            render_clear_tests_section(tid, tank_map)

        render_csv_import_section(tank_map)
        render_localization_section()
        render_weekly_email_section(tank_map)


# ════════════════════════════════════════════════════════════════════════════
# 1) ADD NEW TANK
# ════════════════════════════════════════════════════════════════════════════
def render_add_tank_section() -> None:
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
        for i, param in enumerate([p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]):
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
            new_id = add_tank(name.strip(), volume or None)
            for param, (low, high) in new_ranges.items():
                set_custom_range(new_id, param, low, high)
            st.success(f"Added tank '{name.strip()}' ({volume} L)")
            request_rerun()


# ════════════════════════════════════════════════════════════════════════════
# 2) EDIT / DELETE / VOLUME
# ════════════════════════════════════════════════════════════════════════════
def render_edit_tank_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """✏️ Rename / Delete tank & edit volume for current tank."""
    st.subheader("✏️ Rename/Delete & Edit Volume")

    tid = st.session_state.get("tank_id", 0)
    if tid and tid in tank_map:
        current = tank_map[tid]

        new_name = st.text_input("New name", value=current["name"], key="rename_tank_field")
        new_vol  = st.number_input("Volume (L)", min_value=0.0, step=0.1,
                                   value=current["volume"] or 0.0, key="edit_tank_volume")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", key="save_tank_changes_btn"):
                if new_name.strip() != current["name"]:
                    rename_tank(tid, new_name.strip())
                if (current["volume"] or 0) != new_vol:
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


# ════════════════════════════════════════════════════════════════════════════
# 3) CUSTOM RANGES
# ════════════════════════════════════════════════════════════════════════════
def render_custom_ranges_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """📊 Custom safe ranges for the current tank."""
    st.subheader("📊 Customize Parameter Ranges")

    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Select a tank to customize ranges.")
        return

    params = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
    sel_param = st.selectbox("Parameter", options=params, key="param_select")

    if sel_param:
        low_cur, high_cur = get_custom_range(tid, sel_param) or SAFE_RANGES[sel_param]
        c1, c2 = st.columns(2)
        low_new  = c1.number_input("Safe Low",  value=low_cur,  step=0.1, key=f"low_{sel_param}")
        high_new = c2.number_input("Safe High", value=high_cur, step=0.1, key=f"high_{sel_param}")

        if st.button("Save Custom Range", key="save_custom_range_btn"):
            set_custom_range(tid, sel_param, low_new, high_new)
            st.success(f"Custom range for {sel_param} saved")
            request_rerun()


# ════════════════════════════════════════════════════════════════════════════
# 4) CLEAR ALL TESTS
# ════════════════════════════════════════════════════════════════════════════
def render_clear_tests_section(tid: int, tank_map: Dict[int, Dict[str, Any]]) -> None:
    """🗑️ Delete every water-test row for the current tank (with confirmation)."""
    st.subheader("⚠️ Clear Current Tank's Water Tests")

    # Unique keys per tank
    prep_key   = f"prepare_clear_tests_{tid}"
    confirm_ck = f"clear_confirm_checkbox_{tid}"
    yes_key    = f"confirm_delete_tests_{tid}"
    cancel_key = f"cancel_clear_tests_{tid}"
    flag_key   = f"clear_flag_{tid}"

    if not st.session_state.get(flag_key):
        if st.button("Prepare to clear tests", key=prep_key):
            st.session_state[flag_key] = True
            request_rerun()
    else:
        name = tank_map[tid]["name"]
        st.warning(
            f"🚨 Permanently delete **all** tests for '{name}'. "
            "This action **cannot** be undone."
        )
        confirm = st.checkbox(
            f"I understand and want to delete ALL tests for '{name}'",
            key=confirm_ck,
        )
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if confirm and st.button("Yes, delete all", key=yes_key):
                with get_connection() as conn:
                    conn.execute("DELETE FROM water_tests WHERE tank_id = ?;", (tid,))
                st.success(f"All tests for '{name}' deleted.")
                st.session_state.pop(flag_key, None)
                request_rerun()
        with col_cancel:
            if st.button("Cancel", key=cancel_key):
                st.session_state.pop(flag_key, None)
                st.info("Clear-tests operation cancelled.")
                request_rerun()


# ════════════════════════════════════════════════════════════════════════════
# 5) CSV IMPORT
# ════════════════════════════════════════════════════════════════════════════
def render_csv_import_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """⬇️ Import CSV data into the current tank."""
    st.subheader("⬇️ Import from CSV")
    tid = st.session_state.get("tank_id", 0)

    uploaded = st.file_uploader("Choose CSV", type="csv", key="csv_uploader")

    if uploaded is None:
        return

    if st.button("Import CSV", key="import_csv_btn"):
        try:
            df = pd.read_csv(uploaded)

            # More robust date handling
            if "date" in df.columns:
                try:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df["date"] = df["date"].dt.strftime("%Y-%m-%dT%H:%M:%S").fillna("")
                except Exception as e:
                    st.error(f"Date parsing error: {e}")
                    return

            required = [
                "date", "ph", "ammonia", "nitrite", "nitrate",
                "kh", "gh", "co2_indicator", "temperature", "notes",
            ]
            
            # Explicit column check
            missing = []
            for col in required:
                if col not in df.columns:
                    missing.append(col)
            
            if len(missing) > 0:
                st.error(f"Missing required columns: {', '.join(missing)}")
                return

            # Ensure all required columns exist before proceeding
            df["tank_id"] = tid
            
            with get_connection() as conn:
                # Verify table exists first
                table_exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='water_tests';"
                ).fetchone()
                
                if not table_exists:
                    st.error("Database error: water_tests table doesn't exist")
                    return
                
                # Convert to list of dicts for safer insertion
                records = df.to_dict('records')
                conn.executemany(
                    "INSERT INTO water_tests VALUES (:date, :ph, :ammonia, :nitrite, "
                    ":nitrate, :kh, :gh, :co2_indicator, :temperature, :notes, :tank_id)",
                    records
                )
                
            st.success(f"Successfully imported {len(df)} records to {tank_map[tid]['name']}")
            request_rerun()

        except Exception as e:
            st.error(f"Import failed: {str(e)}")

# ════════════════════════════════════════════════════════════════════════════
# 6) LOCALISATION & UNITS
# ════════════════════════════════════════════════════════════════════════════
def render_localization_section() -> None:
    """🌐 Choose language & unit system (stored in session)."""
    st.subheader("🌐 Localization & Units")
    st.selectbox("Language", list(LOCALIZATIONS.keys()), key="locale")
    st.selectbox("Units",    list(UNIT_SYSTEMS.keys()),  key="units")


# ════════════════════════════════════════════════════════════════════════════
# 7) WEEKLY EMAIL
# ════════════════════════════════════════════════════════════════════════════
def render_weekly_email_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """📧 Weekly summary email settings."""
    st.subheader("📧 Weekly Summary Email")

    settings = get_user_email_settings() or {}

    # Email address
    email = st.text_input("Email", value=settings.get("email", ""), key="email_addr")

    # Tank selection
    options  = list(tank_map.keys())
    default  = settings.get("tanks", [])
    selected = st.multiselect(
        "Tanks to include",
        options=options,
        default=[t for t in default if t in options],
        format_func=lambda tid: tank_map[tid]["name"],
        key="email_tanks",
    )

    # Include switches
    st.markdown("**Include:**")
    inc_keys = [
        ("include_type",  "Maintenance type"),
        ("include_date",  "Date"),
        ("include_notes", "Notes"),
        ("include_cost",  "Cost"),
        ("include_stats", "Stats"),
        ("include_cycle", "Cycle status"),
    ]
    for key, label in inc_keys:
        st.checkbox(label, value=settings.get(key, False), key=key)

    if st.button("Save Email Settings", key="save_email_btn"):
        save_user_email_settings(
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
