# tabs/equipment_tab.py

"""
equipment_tab.py – Equipment Inventory Management

Renders the "Equipment" tab. This allows users to track their aquarium hardware,
such as filters, heaters, CO2 systems, and other equipment on a per-tank basis.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date
import sqlite3

from aqualog_db.repositories import EquipmentRepository
from utils import show_toast

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
    """Render the Equipment inventory tab (scoped to selected tank)."""
    
    st.header("⚙️ Equipment Inventory")

    tank_id: int = st.session_state.get("tank_id", 1)
    if not tank_id:
        st.warning("Please select a tank to manage equipment.")
        return

    equipment_repo = EquipmentRepository()

    # --- "Add New Equipment" Form ---
    with st.expander("➕ Add New Equipment"):
        with st.form("add_equipment_form", clear_on_submit=True):
            new_name = st.text_input("Name*", help="e.g., Fluval FX6 Filter")
            new_category = st.selectbox("Category*", CATEGORIES, index=0)
            new_purchase = st.date_input("Purchase Date (optional)", value=None)
            new_notes = st.text_area("Notes (optional)")

            if st.form_submit_button("✅ Add Equipment"):
                if not new_name.strip():
                    st.error("⚠️ Equipment name is required.")
                else:
                    try:
                        equipment_repo.add_equipment(
                            name=new_name,
                            category=new_category,
                            purchase_date=new_purchase.isoformat() if new_purchase else None,
                            notes=new_notes,
                            tank_id=tank_id,
                        )
                        show_toast("✅ Added", f"Added {new_name} to inventory.")
                        st.rerun()
                    except sqlite3.Error as e:
                        st.error(f"Failed to add equipment: {e}")

    st.markdown("---")

    # --- "My Equipment" List ---
    df = equipment_repo.fetch_for_tank(tank_id)

    if df.empty:
        st.info("No equipment recorded for this tank yet.")
        return

    st.subheader("🗄️ My Equipment")
    to_remove: list[int] = []

    for _, row in df.iterrows():
        eid = int(row["equipment_id"])
        label = f"{row['name']} ({row['category']})"
        
        # Use columns for better layout
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            with st.expander(label):
                st.write(f"• **Category:** {row['category']}")
                if row["purchase_date"]:
                    st.write(f"• **Purchased On:** {row['purchase_date']}")
                if row["notes"]:
                    st.write("• **Notes:**")
                    st.write(row["notes"])
        with col2:
             if st.button("🗑️", key=f"del_eq_{eid}", help="Delete this item"):
                to_remove.append(eid)


    # Bulk delete if any items were marked for removal
    if to_remove:
        try:
            equipment_repo.remove_equipment(to_remove, tank_id)
            show_toast("🗑️ Removed", f"Removed {len(to_remove)} item(s).")
            st.rerun()
        except sqlite3.Error as e:
            st.error(f"Error removing equipment: {e}")