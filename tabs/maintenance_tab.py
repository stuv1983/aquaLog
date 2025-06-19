# tabs/maintenance_tab.py

"""
maintenance_tab.py – Maintenance Log & Scheduler

Renders the "Maintenance" tab for logging and scheduling tasks. Users can record
completed tasks like water changes, define recurring maintenance cycles,
and view a history of all logged maintenance activities for a selected tank.
"""

import streamlit as st
from datetime import date, timedelta # timedelta for calculating next due dates

from aqualog_db.repositories import TankRepository, MaintenanceRepository
from utils import show_toast # Utility for displaying toast notifications

def maintenance_tab() -> None:
    """
    Renders the "Maintenance Log & Scheduler" tab for the AquaLog application.

    This tab provides functionalities to:
    1. Manage recurring maintenance cycles (add, view, delete).
    2. Add new, one-time or cycle-associated maintenance entries.
    3. View a historical log of all maintenance activities for the
       currently selected tank.
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
    tanks = tank_repo.fetch_all()
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
                cycle_type = st.text_input("Type* (e.g. Weekly Water Change)")
                frequency = st.number_input("Frequency (days)*", min_value=1, step=1, value=7)
            with col2:
                is_active = st.checkbox("Active", value=True) # Checkbox to activate/deactivate cycle
                
            cycle_desc = st.text_area("Description (optional)")
            cycle_notes = st.text_area("Notes (optional)")
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
                            description=cycle_desc or None, # Store None if empty string
                            notes=cycle_notes or None,       # Store None if empty string
                            is_active=is_active
                        )
                        show_toast("✅ Maintenance cycle added")
                        st.rerun() # Rerun to refresh the list of existing cycles
                    except Exception as e:
                        st.error(f"Error saving cycle: {e}")

        st.subheader("Existing Maintenance Cycles")
        cycles = maintenance_repo.fetch_maintenance_cycles(tank_id)
        if cycles:
            # Display each existing maintenance cycle in an expander.
            for cycle in cycles:
                with st.expander(f"**{cycle['type']}** (every {cycle['frequency_days']} days)"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.markdown(f"**Status:** {'🟢 Active' if cycle['is_active'] else '⚪ Inactive'}")
                        if cycle.get('description'):
                            st.markdown(f"**Description:** {cycle['description']}")
                        st.markdown(f"**Created:** {cycle['date'][:10]}") # Display date part only
                        if cycle.get('notes'):
                            st.markdown(f"**Notes:** {cycle['notes']}")
                    with col2:
                        # Delete button for each cycle.
                        if st.button("🗑️ Delete", key=f"del_cycle_{cycle['id']}", help="Delete this maintenance cycle"):
                            try:
                                maintenance_repo.delete_maintenance_cycle(cycle['id'])
                                show_toast("⚠️ Cycle deleted")
                                st.rerun() # Rerun to update the list
                            except Exception as e:
                                st.error(f"Error deleting cycle: {e}")
        else:
            st.info("No maintenance cycles defined for this tank.")

    st.subheader("➕ Add New Maintenance Entry")
    
    # Fetch active cycles to allow linking new entries to a cycle.
    active_cycles = [c for c in maintenance_repo.fetch_maintenance_cycles(tank_id) if c['is_active']]
    
    # Initialize selected_cycle_id outside the conditional block
    selected_cycle_id = None 

    # Form for adding a new maintenance log entry.
    with st.form("add_maintenance_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_in = st.date_input("Date*", value=date.today())
        
        with col2:
            if active_cycles:
                # Options for the selectbox: "-- Custom Entry --" or existing cycles.
                cycle_options = [{"label": "-- Custom Entry --", "value": None}] + \
                              [{"label": c['type'], "value": c['id']} for c in active_cycles]
                
                # Selectbox to choose an existing cycle or a custom entry.
                selected_option = st.selectbox(
                    "Select from cycles (optional)", options=cycle_options,
                    format_func=lambda x: x["label"]
                )
                selected_cycle_id = selected_option["value"]
                
                m_type_value = ""
                if selected_cycle_id:
                    # If a cycle is selected, pre-fill the maintenance type and disable editing.
                    selected_cycle = next(c for c in active_cycles if c['id'] == selected_cycle_id)
                    m_type_value = selected_cycle['type']
                    m_type = st.text_input("Type*", value=m_type_value, disabled=True)
                else:
                    # Allow custom type input if no cycle is selected.
                    m_type = st.text_input("Type* (e.g. Water Change)")
            else:
                # If no active cycles, only allow custom type input.
                m_type = st.text_input("Type* (e.g. Water Change)")
        
        description = st.text_area("Description (optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            volume = st.number_input("Volume Changed (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f", value=0.0)
        with col2:
            cost = st.number_input("Cost ($)", min_value=0.0, step=0.01, format="%.2f", value=0.0)
        
        notes = st.text_area("Notes (optional)")
        
        next_due = None
        # Calculate next due date if linked to an active cycle.
        if selected_cycle_id is not None: # Use 'is not None' for explicit check
            # We need to ensure 'selected_cycle' is defined if 'selected_cycle_id' is not None
            if selected_cycle_id in [c['id'] for c in active_cycles]: # Ensure selected_cycle_id is valid
                selected_cycle = next(c for c in active_cycles if c['id'] == selected_cycle_id)
                next_due = date_in + timedelta(days=selected_cycle['frequency_days'])
                st.info(f"Next due will be automatically set to {next_due} based on cycle frequency")
        
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
                        date=date_in.isoformat(), # Convert date to ISO string
                        m_type=final_m_type,
                        description=description or None,
                        volume_changed=volume if volume > 0 else None,
                        cost=cost if cost > 0 else None,
                        notes=notes or None,
                        next_due=next_due.isoformat() if next_due else None,
                        cycle_id=selected_cycle_id
                    )
                    show_toast(f"✅ Entry added for {tank_name}")
                    st.rerun() # Rerun to refresh the history log
                except Exception as e:
                    st.error(f"Error saving entry: {e}")

    st.markdown("---") # Separator

    # --- View Maintenance History Section ---
    # Collapsible expander for viewing past maintenance entries.
    with st.expander("🕒 View Maintenance History", expanded=True):
        rows = maintenance_repo.get_maintenance(tank_id=tank_id) or [] # Fetch history
        if not rows:
            st.info(f"No maintenance records found for {tank_name}.")
        else:
            # Display each maintenance record.
            for row in rows:
                with st.container(border=False): # Use container for visual grouping
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
                                st.rerun() # Rerun to update the history
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
                        st.write(" | ".join(details)) # Display details in a single line
                    
                    if row.get("notes"):
                        st.write(f"📋 Notes: {row['notes']}")
                    
                    st.markdown("---") # Divider between entries