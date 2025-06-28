# sidebar/settings_panel.py

"""
settings_panel.py – Application Settings UI

Renders the collapsible "Settings" panel in the sidebar. Provides the user
interface for adding/editing tanks, customizing parameter ranges, importing
data from CSV, and configuring dashboard layouts and email preferences.
"""

from __future__ import annotations
import sqlite3
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from aqualog_db.repositories import (
    TankRepository,
    CustomRangeRepository,
    EmailSettingsRepository,
    WaterTestRepository
)
from aqualog_db.repositories.tank import TankRecord
from aqualog_db.repositories.email_settings import EmailSettingsRecord

from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES, CO2_ON_SCHEDULE
from utils import request_rerun

def render_analytics_settings() -> None:
    """
    Renders the section for configuring the Data & Analytics tab panels.
    """
    st.subheader("📊 Data & Analytics Tab")
    analytics_panels: Dict[str, str] = {
        "raw_data": "🗂️ Raw Data Table",
        "rolling_avg": "🔄 30-Day Rolling Averages",
        "correlation": "🔗 Correlation Matrix",
        "scatter": "🔍 Scatter & Regression",
        "forecast": "📈 7-Day Forecast",
    }
    st.multiselect(
        "Select and reorder panels to display on the analytics tab",
        options=list(analytics_panels.keys()),
        format_func=lambda key: analytics_panels[key],
        default=list(analytics_panels.keys()),
        key="dashboard_panels"
    )

def render_settings_panel(tank_map: Dict[int, TankRecord]) -> None:
    """
    Renders the entire collapsible "Settings" panel in the Streamlit sidebar.
    """
    tank_repo = TankRepository()
    custom_range_repo = CustomRangeRepository()
    email_repo = EmailSettingsRepository()

    render_add_tank_section(tank_repo, custom_range_repo)
    st.subheader("🔧 Edit Tank Settings")
    render_edit_tank_section(tank_map, tank_repo)
    render_custom_ranges_section(tank_map, custom_range_repo)
    render_co2_schedule_settings(tank_map, tank_repo)
    render_analytics_settings()
    
    tid = st.session_state.get("tank_id", 0)
    if tid:
        render_clear_tests_section(tid, tank_map)
        render_delete_tank_confirmation_section(tid, tank_map, tank_repo)

    render_csv_import_section(tank_map)
    render_localization_section()
    render_weekly_email_section(tank_map, email_repo)


def render_add_tank_section(tank_repo: TankRepository, custom_range_repo: CustomRangeRepository) -> None:
    """
    Renders the section for adding a new tank.
    """
    st.subheader("➕ Add New Tank")
    with st.form("add_new_tank_form", clear_on_submit=True):
        name   = st.text_input("Name*", key="new_tank_name")
        volume = st.number_input("Tank Volume (L)", min_value=0.0, step=0.1,
                                 value=st.session_state.get("new_tank_volume", 0.0),
                                 key="new_tank_volume_input")
        
        init_ranges = st.checkbox("Set initial parameter ranges", key="addtank_init_ranges_checkbox")
        new_ranges: Dict[str, Tuple[float, float]] = {}
        if init_ranges:
            st.info("Enter custom safe ranges for the new tank. Defaults are pre-filled.")
            cols = st.columns(2)
            params_to_show = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
            for i, param in enumerate(params_to_show):
                low_default, high_default = SAFE_RANGES[param]
                col = cols[i % 2]
                low  = col.number_input(f"{param.capitalize()} safe low",  value=low_default,
                                        step=0.1, key=f"new_tank_{param}_low")
                high = col.number_input(f"{param.capitalize()} safe high", value=high_default,
                                        step=0.1, key=f"new_tank_{param}_high")
                new_ranges[param] = (low, high)

        submitted = st.form_submit_button("Add Tank", help="Click to add the new tank to your system.")

    if submitted:
        if not name.strip():
            st.error("⚠️ Tank name cannot be empty. Please provide a name.")
        else:
            try:
                new_tank = tank_repo.add(name.strip(), volume or None)
                new_id = new_tank['id']
                for param, (low, high) in new_ranges.items():
                    custom_range_repo.set(new_id, param, low, high)
                st.success(f"✅ Added tank '{name.strip()}' ({volume} L).")
                request_rerun()
            except ValueError as e:
                st.error(f"❌ Input Error: {e}. Please correct the values.")
            except Exception as e:
                st.error(f"❗ An unexpected error occurred while adding tank: {e}.")
                st.exception(e)


def render_edit_tank_section(tank_map: Dict[int, TankRecord], tank_repo: TankRepository) -> None:
    """
    Renders the section for renaming an existing tank and editing its volume.
    """
    st.subheader("✏️ Rename & Edit Volume")
    tid = st.session_state.get("tank_id", 0)
    if tid and tid in tank_map:
        current = tank_map[tid]
        new_name = st.text_input("New name", value=current["name"], key="rename_tank_field")
        new_vol  = st.number_input("Volume (L)", min_value=0.0, step=0.1,
                                   value=current.get("volume_l") or 0.0,
                                   key="edit_tank_volume_input")

        if st.button("Save Changes", key="save_tank_changes_btn"):
            try:
                changes_made = False
                if new_name.strip() != current["name"]:
                    tank_repo.rename(tid, new_name.strip())
                    changes_made = True
                if (current.get("volume_l") or 0) != new_vol:
                    tank_repo.update_volume(tid, new_vol)
                    changes_made = True

                if changes_made:
                    st.success(f"✅ Updated tank to '{new_name.strip()}' ({new_vol} L).")
                    request_rerun()
                else:
                    st.info("ℹ️ No changes detected to save.")
            except ValueError as e:
                st.error(f"❌ Input Error: {e}. Please correct the values.")
            except Exception as e:
                st.error(f"❗ An unexpected error occurred while saving changes: {e}.")
                st.exception(e)
    else:
        st.info("Select a tank to edit its settings.")

def render_co2_schedule_settings(tank_map: Dict[int, TankRecord], tank_repo: TankRepository) -> None:
    """
    Renders the section for customizing the CO2 injection schedule for the selected tank.
    """
    st.subheader("💨 CO₂ Schedule")
    tid = st.session_state.get("tank_id", 0)
    if not tid or tid not in tank_map:
        st.info("Select a tank to customize its CO₂ schedule.")
        return

    current_tank_info = tank_repo.get_by_id(tid)
    
    default_on_hour, default_off_hour = CO2_ON_SCHEDULE
    current_on_hour = current_tank_info.get("co2_on_hour") if current_tank_info else None
    current_off_hour = current_tank_info.get("co2_off_hour") if current_tank_info else None

    col1, col2 = st.columns(2)
    new_on_hour: Optional[int] = col1.number_input(
        "CO₂ ON Hour (0-23)",
        min_value=0, max_value=23, step=1,
        value=current_on_hour if current_on_hour is not None else default_on_hour,
        format="%d",
        help="Hour (24-hour format) when CO₂ injection starts. Leave blank to use default (9 AM)."
    )
    new_off_hour: Optional[int] = col2.number_input(
        "CO₂ OFF Hour (0-23)",
        min_value=0, max_value=23, step=1,
        value=current_off_hour if current_off_hour is not None else default_off_hour,
        format="%d",
        help="Hour (24-hour format) when CO₂ injection ends. Leave blank to use default (5 PM)."
    )
    
    use_default_on = st.checkbox("Use default CO₂ ON hour", value=(current_on_hour is None))
    use_default_off = st.checkbox("Use default CO₂ OFF hour", value=(current_off_hour is None))

    final_on_hour = None if use_default_on else new_on_hour
    final_off_hour = None if use_default_off else new_off_hour
    
    if st.button("Save CO₂ Schedule", key="save_co2_schedule_btn"):
        try:
            tank_repo.set_co2_schedule(tid, final_on_hour, final_off_hour)
            st.success("✅ CO₂ schedule saved.")
            request_rerun()
        except ValueError as e:
            st.error(f"❌ Input Error: {e}. Please correct the values.")
        except Exception as e:
            st.error(f"❗ An unexpected error occurred: {e}.")
            st.exception(e)

def render_delete_tank_confirmation_section(tid: int, tank_map: Dict[int, TankRecord], tank_repo: TankRepository) -> None:
    """
    Renders the section allowing a user to permanently delete the currently selected tank.
    """
    st.subheader("🗑️ Delete This Tank")
    prep_key = f"prepare_delete_tank_{tid}"
    confirm_ck = f"delete_tank_confirm_checkbox_{tid}"
    yes_key = f"confirm_delete_tank_{tid}"
    cancel_key = f"cancel_delete_tank_{tid}"
    flag_key = f"delete_tank_flag_{tid}"

    if not tid or tid not in tank_map:
        st.info("Select a tank to delete it.")
        return

    if not st.session_state.get(flag_key):
        if st.button("Prepare to Delete Tank", key=prep_key):
            st.session_state[flag_key] = True
            request_rerun()
    else:
        name = tank_map[tid]["name"]
        st.warning(f"🚨 Permanently delete tank **'{name}'** and **ALL** its associated data (water tests, plants, fish, equipment, maintenance). This action **cannot** be undone.")
        confirm = st.checkbox(f"I understand and want to delete ALL tests for '{name}'", key=confirm_ck)
        
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if confirm and st.button("Yes, Delete Tank", key=yes_key):
                try:
                    tank_repo.remove(tid)
                    st.success(f"🗑️ Deleted tank '{name}'.")
                    st.session_state["_delete_tank_flag"] = True
                except Exception as e:
                    st.error(f"❗ An unexpected error occurred while deleting the tank: {e}.")
                    st.exception(e)
                finally:
                    st.session_state.pop(flag_key, None)
                    request_rerun()
        with col_cancel:
            if st.button("Cancel", key=cancel_key):
                st.session_state.pop(flag_key, None)
                st.info("ℹ️ Tank deletion cancelled.")
                request_rerun()

def render_custom_ranges_section(tank_map: Dict[int, TankRecord], custom_range_repo: CustomRangeRepository) -> None:
    """
    Renders the section for customizing parameter safe ranges on a per-tank basis.
    """
    st.subheader("📊 Customize Parameter Ranges")
    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Select a tank to customize its parameter ranges.")
        return
    
    params = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
    sel_param = st.selectbox("Parameter", options=params, key="param_select_custom_range")
    
    if sel_param:
        low_cur, high_cur = custom_range_repo.get(tid, sel_param) or SAFE_RANGES[sel_param]
        c1, c2 = st.columns(2)
        low_new  = c1.number_input("Safe Low",  value=float(low_cur),  step=0.1, key=f"low_{sel_param}_input")
        high_new = c2.number_input("Safe High", value=float(high_cur), step=0.1, key=f"high_{sel_param}_input")
        
        if st.button("Save Custom Range", key="save_custom_range_btn"):
            try:
                custom_range_repo.set(tid, sel_param, low_new, high_new)
                st.success(f"✅ Custom range for {sel_param.capitalize()} saved.")
                request_rerun()
            except ValueError as e:
                st.error(f"❌ Input Error: {e}. Please correct the values.")
            except Exception as e:
                st.error(f"❗ An unexpected error occurred: {e}.")
                st.exception(e)

def render_clear_tests_section(tid: int, tank_map: Dict[int, TankRecord]) -> None:
    """
    Renders the section allowing a user to permanently delete all water tests
    for the currently selected tank.
    """
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
                    try:
                        conn.execute("DELETE FROM water_tests WHERE tank_id = ?;", (tid,))
                        conn.commit()
                        st.success(f"✅ All tests for '{name}' deleted.")
                    except sqlite3.Error as e:
                        st.error(f"❌ Error deleting tests: {e}")
                        conn.rollback()
                        st.exception(e)
                st.session_state.pop(flag_key, None)
                request_rerun()
        with col_cancel:
            if st.button("Cancel", key=cancel_key):
                st.session_state.pop(flag_key, None)
                st.info("ℹ️ Clear-tests operation cancelled.")
                request_rerun()

def render_csv_import_section(tank_map: Dict[int, TankRecord]) -> None:
    """
    Renders the section for importing water test data from a CSV file.
    """
    st.subheader("⬇️ Import from CSV")
    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Please select a tank before importing data.")
        return
    
    uploaded = st.file_uploader("Choose CSV", type="csv", key="csv_uploader_settings")
    if not uploaded:
        return
    
    if st.button("Import CSV", key="import_csv_btn"):
        df_to_insert: pd.DataFrame = pd.DataFrame() # Initialize df_to_insert here
        try:
            df = pd.read_csv(uploaded)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            
            if "date" not in df.columns:
                st.error("❌ CSV must contain a 'date' column.")
                return
            
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
            df.dropna(subset=['date'], inplace=True)
            
            if df.empty:
                st.error("❌ No valid date entries found in the CSV after parsing. Please ensure your 'date' column is correctly formatted.")
                return

            df["tank_id"] = tid
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(water_tests);")
                db_columns = {row[1] for row in cursor.fetchall()}
            
            df_to_insert = df[[col for col in df.columns if col in db_columns]]
            
            if df_to_insert.empty:
                st.warning("⚠️ No recognized data columns found in the CSV to import. Check CSV headers against expected water test parameters.")
                return

            with get_connection() as conn:
                for d in df_to_insert["date"].unique():
                    conn.execute("DELETE FROM water_tests WHERE date = ? AND tank_id = ?;", (d, tid))
                
                df_to_insert.to_sql("water_tests", conn, if_exists="append", index=False)
                conn.commit()
            
            st.success(f"✅ Imported {len(df_to_insert)} records into '{tank_map[tid]['name']}'.")
            request_rerun()
        except pd.errors.EmptyDataError:
            st.error("❌ The uploaded CSV file is empty. Please upload a CSV with data.")
        except Exception as e:
            st.error(f"❌ Import failed: {e}. Please check the CSV format and try again.")
            st.exception(e)

def render_localization_section() -> None:
    """
    Renders the section for selecting application language and unit system.
    """
    st.subheader("🌐 Localization & Units")
    st.selectbox("Language", list(LOCALIZATIONS.keys()), key="locale")
    st.selectbox("Units", list(UNIT_SYSTEMS.keys()), key="units")

def render_weekly_email_section(tank_map: Dict[int, TankRecord], email_repo: EmailSettingsRepository) -> None:
    """
    Renders the section for configuring weekly email summaries.
    """
    st.subheader("📧 Weekly Summary Email")
    settings: EmailSettingsRecord = email_repo.get() or {}

    email = st.text_input("Recipient Email", value=settings.get("email", ""), key="email_addr")
    
    options: List[int]  = list(tank_map.keys())
    try:
        default_tanks: List[int] = settings.get("tanks", [])
    except Exception:
        default_tanks = []

    selected = st.multiselect(
        "Tanks to include in summary",
        options=options,
        default=[t for t in default_tanks if t in options],
        format_func=lambda tid: tank_map[tid]["name"],
        key="email_tanks",
    )
    
    st.markdown("**Include the following in the email:**")
    inc_keys: List[Tuple[str, str]] = [
        ("include_type", "Maintenance type"),
        ("include_date", "Date"),
        ("include_notes", "Notes"),
        ("include_cost", "Cost"),
        ("include_stats", "Water Test Stats (pH, Ammonia, etc.)"),
        ("include_cycle", "Nitrogen Cycle status"),
    ]
    
    for key, label in inc_keys:
        st.checkbox(label, value=settings.get(key, False), key=key)
    
    if st.button("Save Email Settings", key="save_email_btn"):
        try:
            email_repo.save(
                email=email,
                tanks=selected,
                include_type=st.session_state.get("include_type", False),
                include_date=st.session_state.get("include_date", False),
                include_notes=st.session_state.get("include_notes", False),
                include_cost=st.session_state.get("include_cost", False),
                include_stats=st.session_state.get("include_stats", False),
                include_cycle=st.session_state.get("include_cycle", False),
            )
            st.success("✅ Email settings saved successfully!")
            request_rerun()
        except ValueError as e:
            st.error(f"❌ Error saving email settings: {e}")
        except Exception as e:
            st.error(f"❗ An unexpected error occurred: {e}")
            st.exception(e)