# tabs/equipment_tab.py

"""
equipment_tab.py – Equipment Inventory Management

Renders the "Equipment" tab. This allows users to track their aquarium hardware,
such as filters, heaters, CO2 systems, and other equipment on a per-tank basis.
Users can add new equipment, view existing equipment, and remove items from
their inventory.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date # Imported for date_input, though value=None is used
import sqlite3 # Imported for specific exception handling

from aqualog_db.repositories import EquipmentRepository
from utils import show_toast

# Define a list of predefined categories for equipment, enhancing consistency.
CATEGORIES = [
    "Filters",
    "Air Pumps & Stones",
    "CO₂ Bottle",
    "Fertilizers",
    "Seachem Products",
    "Lighting",
    "Heater",
    "Substrate",
    "Other",
]

def equipment_tab() -> None:
    """
    Renders the "Equipment Inventory" tab for the AquaLog application.

    This tab allows users to manage their aquarium equipment. It provides a form
    to add new equipment items and displays a list of existing equipment
    for the currently selected tank, with options to remove them.
    All operations are scoped to the `tank_id` stored in `st.session_state`.
    """
    
    st.header("⚙️ Equipment Inventory")

    # Retrieve the currently selected tank ID from Streamlit's session state.
    tank_id: int = st.session_state.get("tank_id", 1)
    if not tank_id:
        st.warning("Please select a tank to manage equipment.")
        return

    equipment_repo = EquipmentRepository()

    # --- "Add New Equipment" Form ---
    # Use a Streamlit expander for the add form to keep the UI clean.
    with st.expander("➕ Add New Equipment"):
        # Use a Streamlit form to group input widgets and a submit button.
        # `clear_on_submit=True` clears the form fields after successful submission.
        with st.form("add_equipment_form", clear_on_submit=True):
            new_name = st.text_input("Name*", help="e.g., Fluval FX6 Filter")
            new_category = st.selectbox("Category*", CATEGORIES, index=0) # Dropdown for predefined categories
            new_purchase = st.date_input("Purchase Date (optional)", value=None) # Optional date picker
            new_notes = st.text_area("Notes (optional)")

            # Form submission button
            if st.form_submit_button("✅ Add Equipment"):
                if not new_name.strip():
                    # Basic validation: Equipment name cannot be empty
                    st.error("⚠️ Equipment name is required.")
                else:
                    try:
                        # Call repository to add the new equipment record
                        equipment_repo.add_equipment(
                            name=new_name,
                            category=new_category,
                            purchase_date=new_purchase.isoformat() if new_purchase else None, # Convert date to ISO string
                            notes=new_notes,
                            tank_id=tank_id,
                        )
                        show_toast("✅ Added", f"Added {new_name} to inventory.")
                        st.rerun() # Rerun the app to update the equipment list
                    except sqlite3.Error as e:
                        st.error(f"Failed to add equipment: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")

    st.markdown("---") # Separator

    # --- "My Equipment" List ---
    st.subheader("🗄️ My Equipment")
    # Fetch all equipment for the current tank
    df = equipment_repo.fetch_for_tank(tank_id)

    if df.empty:
        st.info("No equipment recorded for this tank yet. Use the 'Add New Equipment' section above.")
        return

    # List to store IDs of equipment marked for removal.
    to_remove: list[int] = []

    # Iterate through each equipment item and display it
    for _, row in df.iterrows():
        eid = int(row["equipment_id"])
        label = f"**{row['name']}** ({row['category']})" # Display name and category
        
        # Use columns for a structured layout of each equipment item.
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            # Use an expander for details to keep the main list concise.
            with st.expander(label):
                st.write(f"• **Category:** {row['category']}")
                if row["purchase_date"]:
                    st.write(f"• **Purchased On:** {row['purchase_date']}")
                if row["notes"]:
                    st.write("• **Notes:**")
                    st.write(row["notes"])
        with col2:
            # Delete button for each item. Adds its ID to `to_remove` list.
            if st.button("🗑️", key=f"del_eq_{eid}", help="Delete this item from inventory"):
                to_remove.append(eid)


    # Perform bulk deletion if any items were marked for removal.
    # This is done outside the loop to avoid modifying the DataFrame while iterating.
    if to_remove:
        try:
            equipment_repo.remove_equipment(to_remove, tank_id)
            show_toast("🗑️ Removed", f"Removed {len(to_remove)} item(s) from inventory.")
            st.rerun() # Rerun to reflect deletions in the UI
        except sqlite3.Error as e:
            st.error(f"Error removing equipment: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")