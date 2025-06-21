# sidebar/settings_panel.py

"""
settings_panel.py – Application Settings UI

Renders the collapsible "Settings" panel in the sidebar. Provides the user
interface for adding/editing tanks, customizing parameter ranges, importing
data from CSV, and configuring dashboard layouts and email preferences.
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
    WaterTestRepository # Added for CSV import functionality
)
from config import LOCALIZATIONS, UNIT_SYSTEMS, SAFE_RANGES
from utils import request_rerun

def render_analytics_settings():
    """
    Renders the section for configuring the Data & Analytics tab panels.

    Allows users to select and reorder which analytical panels are displayed
    on the 'Data & Analytics' tab.
    """
    st.subheader("📊 Data & Analytics Tab")
    # Define available panels with user-friendly labels
    analytics_panels = {
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
        default=list(analytics_panels.keys()), # All panels are selected by default
        key="dashboard_panels" # Stores selected panels in session state
    )

def render_settings_panel(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """
    Renders the entire collapsible settings panel in the Streamlit sidebar.

    This function orchestrates the rendering of various sub-sections for
    managing tanks, custom ranges, analytics display, data import,
    localization, and email settings.

    Args:
        tank_map: A dictionary mapping tank IDs to their details (name, volume).
                  Used to populate tank selectors and display current tank info.
    """
    tank_repo = TankRepository()
    custom_range_repo = CustomRangeRepository()
    email_repo = EmailSettingsRepository()

    render_add_tank_section(tank_repo, custom_range_repo)
    st.subheader("🔧 Edit Tank Settings")
    render_edit_tank_section(tank_map, tank_repo)
    render_custom_ranges_section(tank_map, custom_range_repo)
    render_analytics_settings()
    
    # Get the currently selected tank ID from session state
    tid = st.session_state.get("tank_id", 0)
    if tid: # Only show clear tests option if a tank is selected
        render_clear_tests_section(tid, tank_map)

    render_csv_import_section(tank_map)
    render_localization_section()
    render_weekly_email_section(tank_map, email_repo)


def render_add_tank_section(tank_repo: TankRepository, custom_range_repo: CustomRangeRepository) -> None:
    """
    Renders the section for adding a new tank.

    Allows users to specify a tank name, volume, and optionally set initial
    custom parameter ranges for the new tank.

    Args:
        tank_repo: The TankRepository instance for database operations.
        custom_range_repo: The CustomRangeRepository instance for setting initial ranges.
    """
    st.subheader("➕ Add New Tank")
    # Use Streamlit forms to group input widgets and a submit button
    with st.form("add_new_tank_form", clear_on_submit=True):
        name   = st.text_input("Name", key="new_tank_name")
        volume = st.number_input("Tank Volume (L)", min_value=0.0, step=0.1,
                                 value=st.session_state.get("new_tank_volume", 0.0),
                                 key="new_tank_volume_input") # Unique key for this input
        
        init_ranges = st.checkbox("Set initial parameter ranges", key="addtank_init_ranges_checkbox")
        new_ranges: Dict[str, Tuple[float, float]] = {}
        if init_ranges:
            st.info("Enter custom safe ranges for the new tank. Defaults are pre-filled.")
            cols = st.columns(2)
            # Exclude 'co2_indicator' and 'ammonia' from custom ranges as they have specific handling
            params_to_show = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
            for i, param in enumerate(params_to_show):
                low_default, high_default = SAFE_RANGES[param]
                col = cols[i % 2] # Distribute inputs into two columns
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
                # Add the new tank to the database
                new_tank = tank_repo.add(name.strip(), volume or None)
                new_id = new_tank['id']
                # If custom ranges were specified, save them
                for param, (low, high) in new_ranges.items():
                    custom_range_repo.set(new_id, param, low, high)
                st.success(f"✅ Added tank '{name.strip()}' ({volume} L).")
                request_rerun() # Rerun to update sidebar tank selector
            except ValueError as e: # Catch specific validation errors from the repository
                st.error(f"❌ Input Error: {e}. Please correct the values.")
            except Exception as e:
                st.error(f"❗ An unexpected error occurred while adding tank: {e}.")
                # Log the full traceback for debugging (if a logging setup were in place)


def render_edit_tank_section(tank_map: Dict[int, Dict[str, Any]], tank_repo: TankRepository) -> None:
    """
    Renders the section for renaming, editing the volume, or deleting an existing tank.

    Args:
        tank_map: A dictionary mapping tank IDs to their details.
        tank_repo: The TankRepository instance for database operations.
    """
    st.subheader("✏️ Rename/Delete & Edit Volume")
    tid = st.session_state.get("tank_id", 0)
    if tid and tid in tank_map:
        current = tank_map[tid]
        new_name = st.text_input("New name", value=current["name"], key="rename_tank_field")
        new_vol  = st.number_input("Volume (L)", min_value=0.0, step=0.1,
                                   value=current.get("volume") or 0.0, key="edit_tank_volume_input")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", key="save_tank_changes_btn"):
                try:
                    # Use a flag to track if any actual update occurred
                    changes_made = False
                    if new_name.strip() != current["name"]:
                        tank_repo.rename(tid, new_name.strip())
                        changes_made = True
                    if (current.get("volume") or 0) != new_vol:
                        tank_repo.update_volume(tid, new_vol)
                        changes_made = True

                    if changes_made:
                        st.success(f"✅ Updated tank to '{new_name.strip()}' ({new_vol} L).")
                        request_rerun()
                    else:
                        st.info("ℹ️ No changes detected to save.")
                except ValueError as e: # Catch specific validation errors from the repository
                    st.error(f"❌ Input Error: {e}. Please correct the values.")
                except Exception as e:
                    st.error(f"❗ An unexpected error occurred while saving changes: {e}.")
                    # Log the full traceback for debugging
        with col2:
            if st.button("Delete This Tank", key="delete_tank_btn"):
                try:
                    # Confirm deletion to user (handled by Streamlit's button behavior)
                    tank_repo.remove(tid)
                    st.success(f"🗑️ Deleted tank '{current['name']}'.")
                    request_rerun() # Rerun to update UI after deletion
                except Exception as e:
                    st.error(f"❗ Error deleting tank: {e}.")
                    # Log the full traceback for debugging
    else:
        st.info("Select a tank to edit its settings.")

def render_custom_ranges_section(tank_map: Dict[int, Dict[str, Any]], custom_range_repo: CustomRangeRepository) -> None:
    """
    Renders the section for customizing parameter safe ranges on a per-tank basis.

    Allows users to override default safe ranges for pH, KH, GH, temperature,
    nitrate, nitrite, and ammonia.

    Args:
        tank_map: A dictionary mapping tank IDs to their details.
        custom_range_repo: The CustomRangeRepository instance for database operations.
    """
    st.subheader("📊 Customize Parameter Ranges")
    tid = st.session_state.get("tank_id", 0)
    if not tid:
        st.info("Select a tank to customize its parameter ranges.")
        return
    
    # Parameters for which custom ranges can be set (excluding CO2 indicator)
    params = [p for p in SAFE_RANGES if p not in ("co2_indicator", "ammonia")]
    sel_param = st.selectbox("Parameter", options=params, key="param_select_custom_range")
    
    if sel_param:
        # Get current custom range or fall back to global safe range
        low_cur, high_cur = custom_range_repo.get(tid, sel_param) or SAFE_RANGES[sel_param]
        c1, c2 = st.columns(2)
        low_new  = c1.number_input("Safe Low",  value=float(low_cur),  step=0.1, key=f"low_{sel_param}_input")
        high_new = c2.number_input("Safe High", value=float(high_cur), step=0.1, key=f"high_{sel_param}_input")
        
        if st.button("Save Custom Range", key="save_custom_range_btn"):
            try:
                custom_range_repo.set(tid, sel_param, low_new, high_new)
                st.success(f"✅ Custom range for {sel_param.capitalize()} saved.")
                request_rerun()
            except ValueError as e: # Catch specific validation errors from the repository
                st.error(f"❌ Input Error: {e}. Please correct the values.")
            except Exception as e:
                st.error(f"❗ An unexpected error occurred: {e}.")
                # Log the full traceback for debugging

def render_clear_tests_section(tid: int, tank_map: Dict[int, Dict[str, Any]]) -> None:
    """
    Renders the section allowing a user to permanently delete all water tests
    for the currently selected tank. Includes confirmation steps.

    Args:
        tid: The ID of the currently selected tank.
        tank_map: A dictionary mapping tank IDs to their details.
    """
    st.subheader("⚠️ Clear Current Tank's Water Tests")
    # Use unique keys to maintain state across reruns
    prep_key = f"prepare_clear_tests_{tid}"
    confirm_ck = f"clear_confirm_checkbox_{tid}"
    yes_key = f"confirm_delete_tests_{tid}"
    cancel_key = f"cancel_clear_tests_{tid}"
    flag_key = f"clear_flag_{tid}" # Session state flag to control visibility of confirmation

    # Initial button to trigger the confirmation process
    if not st.session_state.get(flag_key):
        if st.button("Prepare to clear tests", key=prep_key):
            st.session_state[flag_key] = True
            request_rerun() # Rerun to show confirmation UI
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
                st.session_state.pop(flag_key, None) # Clear flag after action
                request_rerun()
        with col_cancel:
            if st.button("Cancel", key=cancel_key):
                st.session_state.pop(flag_key, None)
                st.info("ℹ️ Clear-tests operation cancelled.")
                request_rerun()

def render_csv_import_section(tank_map: Dict[int, Dict[str, Any]]) -> None:
    """
    Renders the section for importing water test data from a CSV file.

    Data is imported for the currently selected tank, with existing entries
    for the same date being replaced.

    Args:
        tank_map: A dictionary mapping tank IDs to their details.
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
        try:
            df = pd.read_csv(uploaded)
            df.columns = df.columns.str.strip().str.lower() # Clean column names
            
            # Drop 'id' column if present, as it's typically auto-incremented in DB
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            
            if "date" not in df.columns:
                st.error("❌ CSV must contain a 'date' column.")
                return
            
            # Convert 'date' column to datetime and format for ISO string storage
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
            df.dropna(subset=['date'], inplace=True) # Remove rows where date conversion failed
            
            if df.empty: # Check if all rows were dropped due to bad dates
                st.error("❌ No valid date entries found in the CSV after parsing. Please ensure your 'date' column is correctly formatted.")
                return

            df["tank_id"] = tid # Assign all imported records to the current tank
            
            with get_connection() as conn:
                cursor = conn.cursor()
                # Get actual column names from the 'water_tests' table to ensure valid insertion
                cursor.execute("PRAGMA table_info(water_tests);")
                db_columns = {row[1] for row in cursor.fetchall()}
            
            # Filter DataFrame to include only columns that exist in the database table
            df_to_insert = df[[col for col in df.columns if col in db_columns]]
            
            if df_to_insert.empty:
                st.warning("⚠️ No recognized data columns found in the CSV to import. Check CSV headers against expected water test parameters.")
                return

            with get_connection() as conn:
                # Delete existing records for the same dates in this tank to prevent duplicates
                # This ensures an "upsert" behavior where new data replaces old data for given dates
                for d in df_to_insert["date"].unique():
                    conn.execute("DELETE FROM water_tests WHERE date = ? AND tank_id = ?;", (d, tid))
                
                # Insert the prepared DataFrame into the water_tests table
                df_to_insert.to_sql("water_tests", conn, if_exists="append", index=False)
                conn.commit() # Explicitly commit after to_sql
            
            st.success(f"✅ Imported {len(df_to_insert)} records into '{tank_map[tid]['name']}'.")
            request_rerun()
        except pd.errors.EmptyDataError:
            st.error("❌ The uploaded CSV file is empty. Please upload a CSV with data.")
        except Exception as e:
            st.error(f"❌ Import failed: {e}. Please check the CSV format and try again.")
            # Log the full traceback for developer debugging

def render_localization_section() -> None:
    """
    Renders the section for selecting application language and unit system.

    Changes made here will affect how values are displayed throughout the app.
    """
    st.subheader("🌐 Localization & Units")
    # Streamlit selectbox to choose locale/language
    st.selectbox("Language", list(LOCALIZATIONS.keys()), key="locale")
    # Streamlit selectbox to choose unit system (e.g., Metric, Imperial)
    st.selectbox("Units", list(UNIT_SYSTEMS.keys()), key="units")

def render_weekly_email_section(tank_map: Dict[int, Dict[str, Any]], email_repo: EmailSettingsRepository) -> None:
    """
    Renders the section for configuring weekly email summaries.

    Allows users to set an email address, select tanks to include in the summary,
    and choose which data fields to include in the report.

    Args:
        tank_map: A dictionary mapping tank IDs to their details.
        email_repo: The EmailSettingsRepository instance for database operations.
    """
    st.subheader("📧 Weekly Summary Email")
    # Retrieve current email settings from the database
    settings = email_repo.get() or {} # Use empty dict if no settings are found

    email = st.text_input("Recipient Email", value=settings.get("email", ""), key="email_addr")
    
    options  = list(tank_map.keys()) # Available tank IDs
    # Get default selected tanks from current settings, ensuring they are valid options
    try:
        default_tanks = settings.get("tanks", [])
    except Exception: # Handle potential issues if 'tanks' field is malformed
        default_tanks = []

    selected = st.multiselect(
        "Tanks to include in summary",
        options=options,
        default=[t for t in default_tanks if t in options], # Filter defaults to existing tanks
        format_func=lambda tid: tank_map[tid]["name"], # Display tank names
        key="email_tanks",
    )
    
    st.markdown("**Include the following in the email:**")
    # Define checkboxes for including specific data points in the email
    inc_keys = [
        ("include_type", "Maintenance type"),
        ("include_date", "Date"),
        ("include_notes", "Notes"),
        ("include_cost", "Cost"),
        ("include_stats", "Water Test Stats (pH, Ammonia, etc.)"),
        ("include_cycle", "Nitrogen Cycle status"),
    ]
    
    for key, label in inc_keys:
        st.checkbox(label, value=settings.get(key, False), key=key) # Default to False if not set
    
    if st.button("Save Email Settings", key="save_email_btn"):
        try:
            # Save all settings from session state
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
            st.success("✅ Email settings saved successfully!")
            request_rerun()
        except ValueError as e:
            st.error(f"❌ Error saving email settings: {e}")
        except Exception as e:
            st.error(f"❗ An unexpected error occurred: {e}")
            # Log the full traceback for developer debugging