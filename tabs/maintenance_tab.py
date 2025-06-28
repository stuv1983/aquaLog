# tabs/maintenance_tab.py

"""
maintenance_tab.py – Maintenance Log & Scheduler

Renders the "Maintenance" tab for logging and scheduling tasks. Users can record
completed tasks like water changes, define recurring maintenance cycles,
and view a history of all logged maintenance activities for a selected tank.
"""

from __future__ import annotations
import streamlit as st
from datetime import date, timedelta
from typing import List # Ensure List is imported for clearer type hints

from aqualog_db.repositories import TankRepository, MaintenanceRepository
from aqualog_db.repositories.tank import TankRecord # Import TankRecord
from aqualog_db.repositories.maintenance import MaintenanceLogRecord, MaintenanceCycleRecord # Import Maintenance TypedDicts

from utils import show_toast

def maintenance_tab() -> None:
    """
    Renders the "Maintenance Log & Scheduler" tab for the AquaLog application.

    This tab provides functionalities to:
    1.  **Manage Maintenance Cycles:** Define, view, and delete recurring maintenance tasks
        (e.g., weekly water changes) for the selected tank.
    2.  **Add New Maintenance Entry:** Log individual maintenance events, which can be
        one-time tasks or linked to a defined recurring cycle.
    3.  **View Maintenance History:** Display a chronological log of all past maintenance
        activities for the currently selected tank, with options to delete records.

    All operations are scoped to the `tank_id` retrieved from `st.session_state`.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    
    # Retrieve the currently selected tank ID from Streamlit's session state.
    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank from the sidebar to manage maintenance.")
        return

    # Instantiate repository classes for database interactions.
    tank_repo = TankRepository()
    maintenance_repo = MaintenanceRepository()

    # Fetch tank details to display the tank name in the header.
    tanks: List[TankRecord] = tank_repo.fetch_all() # Explicitly type tanks as List[TankRecord]
    if not tanks:
        st.warning("No tanks found. Please add a tank in Settings first.")
        return
        
    tank_names = {t["id"]: t["name"] for t in tanks}
    tank_name = tank_names.get(tank_id, f"Tank #{tank_id}")

    st.header(f"🛠️ Maintenance — {tank_name}")
    
    # --- Manage Maintenance Cycles Section ---
    # This section allows users to define recurring maintenance tasks.
    with st.expander("🔄 Manage Maintenance Cycles", expanded=False):
        st.subheader("Add New Maintenance Cycle")
        with st.form("add_cycle_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cycle_type = st.text_input("Type* (e.g. Weekly Water Change)", help="e.g., Weekly Water Change, Filter Cleaning")
                frequency = st.number_input("Frequency (days)*", min_value=1, step=1, value=7, help="How often this task repeats in days (e.g., 7 for weekly)")
            with col2:
                is_active = st.checkbox("Active", value=True, help="Set to inactive if this cycle is no longer performed regularly.")
                
            cycle_desc = st.text_area("Description (optional)", help="A brief description of this cycle.")
            cycle_notes = st.text_area("Notes (optional)", help="Any additional notes about this recurring cycle.")
            submitted = st.form_submit_button("💾 Save Cycle")

            if submitted:
                if not cycle_type:
                    show_toast("❌ Cycle type is required", icon="⚠️")
                else:
                    try:
                        maintenance_repo.save_maintenance_cycle(
                            tank_id=tank_id,
                            maintenance_type=cycle_type,
                            frequency_days=frequency,
                            description=cycle_desc or None,
                            notes=cycle_notes or None,
                            is_active=is_active
                        )
                        show_toast("✅ Maintenance cycle added")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving cycle: {e}")

        st.subheader("Existing Maintenance Cycles")
        cycles: List[MaintenanceCycleRecord] = maintenance_repo.fetch_maintenance_cycles(tank_id) # Explicitly type cycles
        if cycles:
            # Display each existing maintenance cycle in an expander.
            for cycle in cycles:
                with st.expander(f"**{cycle['type']}** (every {cycle['frequency_days']} days)"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.markdown(f"**Status:** {'🟢 Active' if cycle['is_active'] else '⚪ Inactive'}")
                        if cycle.get('description'):
                            st.markdown(f"**Description:** {cycle['description']}")
                        st.markdown(f"**Created:** {cycle['date'][:10]}")
                        if cycle.get('notes'):
                            st.markdown(f"**Notes:** {cycle['notes']}")
                    with col2:
                        # Delete button for each cycle.
                        if st.button("🗑️ Delete", key=f"del_cycle_{cycle['id']}", help="Delete this maintenance cycle"):
                            try:
                                maintenance_repo.delete_maintenance_cycle(cycle['id'])
                                show_toast("⚠️ Cycle deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting cycle: {e}")
        else:
            st.info("No maintenance cycles defined for this tank.")

    st.subheader("➕ Add New Maintenance Entry")
    
    # Fetch active cycles to allow linking new entries to a cycle.
    active_cycles: List[MaintenanceCycleRecord] = [c for c in maintenance_repo.fetch_maintenance_cycles(tank_id) if c['is_active']] # Explicitly type active_cycles
    
    # Initialize selected_cycle_id outside the conditional block
    selected_cycle_id = None 

    # Form for adding a new maintenance log entry.
    with st.form("add_maintenance_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_in = st.date_input("Date*", value=date.today(), help="The date the maintenance was performed.")
        
        with col2:
            if active_cycles:
                # Options for the selectbox: "-- Custom Entry --" or existing cycles.
                cycle_options = [{"label": "-- Custom Entry --", "value": None}] + \
                              [{"label": c['type'], "value": c['id']} for c in active_cycles]
                
                # Selectbox to choose an existing cycle or a custom entry.
                selected_option = st.selectbox(
                    "Select from cycles (optional)", options=cycle_options,
                    format_func=lambda x: x["label"],
                    help="Link this entry to an existing recurring cycle, or choose 'Custom Entry'."
                )
                selected_cycle_id = selected_option["value"]
                
                m_type_value = ""
                if selected_cycle_id:
                    # If a cycle is selected, pre-fill the maintenance type and disable editing.
                    selected_cycle = next(c for c in active_cycles if c['id'] == selected_cycle_id)
                    m_type_value = selected_cycle['type']
                    m_type = st.text_input("Type*", value=m_type_value, disabled=True, help="The type of maintenance performed.")
                else:
                    # Allow custom type input if no cycle is selected.
                    m_type = st.text_input("Type* (e.g. Water Change)", help="The type of maintenance performed (e.g., Water Change, Filter Cleaning).")
            else:
                # If no active cycles, only allow custom type input.
                m_type = st.text_input("Type* (e.g. Water Change)", help="The type of maintenance performed (e.g., Water Change, Filter Cleaning).")
        
        description = st.text_area("Description (optional)", help="A brief description of this specific maintenance event.")
        
        col1, col2 = st.columns(2)
        with col1:
            volume = st.number_input("Volume Changed (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f", value=0.0, help="Percentage of water changed (e.g., 25.0, 50.0).")
        with col2:
            cost = st.number_input("Cost ($)", min_value=0.0, step=0.01, format="%.2f", value=0.0, help="Cost associated with this maintenance (e.g., new filter media, chemicals).")
        
        notes = st.text_area("Notes (optional)", help="Any additional notes about this specific event.")
        
        next_due = None
        # Calculate next due date if linked to an active cycle.
        if selected_cycle_id is not None:
            if selected_cycle_id in [c['id'] for c in active_cycles]:
                selected_cycle = next(c for c in active_cycles if c['id'] == selected_cycle_id)
                next_due = date_in + timedelta(days=selected_cycle['frequency_days'])
                st.info(f"Next due will be automatically set to {next_due.strftime('%Y-%m-%d')} based on cycle frequency")
        
        submitted = st.form_submit_button("💾 Save Entry")

        if submitted:
            # Determine the final maintenance type based on user input or selected cycle.
            final_m_type = m_type_value if selected_cycle_id is not None else m_type
            if not final_m_type:
                show_toast("❌ Maintenance type is required", icon="⚠️")
            else:
                try:
                    maintenance_repo.save_maintenance(
                        tank_id=tank_id,
                        date=date_in.isoformat(),
                        m_type=final_m_type,
                        description=description or None,
                        volume_changed=volume if volume > 0 else None,
                        cost=cost if cost > 0 else None,
                        notes=notes or None,
                        next_due=next_due.isoformat() if next_due else None,
                        cycle_id=selected_cycle_id
                    )
                    show_toast(f"✅ Entry added for {tank_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving entry: {e}")

    st.markdown("---")

    # --- View Maintenance History Section ---
    # Collapsible expander for viewing past maintenance entries.
    with st.expander("🕒 View Maintenance History", expanded=True):
        rows: List[MaintenanceLogRecord] = maintenance_repo.get_maintenance(tank_id=tank_id) or [] # Explicitly type rows
        if not rows:
            st.info(f"No maintenance records found for {tank_name}.")
        else:
            # Display each maintenance record.
            for row in rows:
                with st.container(border=False):
                    col1, col2 = st.columns([4,1])
                    with col1:
                        st.markdown(f"**{row['date'][:10]} – {row['maintenance_type']}**")
                        if row.get('cycle_name'):
                            st.caption(f"Part of cycle: {row['cycle_name']}")
                    with col2:
                        # Delete button for each record.
                        if st.button("🗑️", key=f"del_maint_{row['id']}", help="Delete this record"):
                            try:
                                maintenance_repo.delete_maintenance(row['id'])
                                show_toast("⚠️ Record deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting record: {e}")
                    
                    if row.get("description"):
                        st.write(f"📝 {row['description']}")
                    
                    details = []
                    if row.get("volume_changed") is not None:
                        details.append(f"💧 {row['volume_changed']}% water")
                    if row.get("cost") is not None:
                        details.append(f"💵 ${row['cost']:.2f}")
                    if row.get("next_due"):
                        details.append(f"⏳ Next due: {row['next_due'][:10]}")
                    
                    if details:
                        st.write(" | ".join(details))
                    
                    if row.get("notes"):
                        st.write(f"📋 Notes: {row['notes']}")
                    
                    st.markdown("---")