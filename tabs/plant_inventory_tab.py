# tabs/plant_inventory_tab.py

"""
plant_inventory_tab.py – Plant Inventory Management

Renders the "Plants" tab. Allows users to search a master database of aquatic
plants, add plants to their specific tank's inventory, and add new, unlisted
plant species to the master database. It also displays and allows management
of the current plant inventory for the selected tank.
"""

from __future__ import annotations
import pandas as pd
import streamlit as st
from aqualog_db.repositories import TankRepository, PlantRepository, OwnedPlantRepository
from .inventory_tab_helpers import render_inventory_search, render_add_new_item_form

def _display_plant_details(row: pd.Series) -> None:
    """Displays the details for a plant."""
    name = row.get('plant_name', 'Unnamed plant')
    st.subheader(name)
    exclude_cols = ['plant_id', 'plant_name', 'thumbnail_url']
    for col_name in row.index:
        if col_name not in exclude_cols and pd.notna(row[col_name]) and str(row[col_name]).strip():
            display_label = col_name.replace('_', ' ').title()
            st.write(f"**{display_label}:** {row[col_name]}")

def _plant_form_fields() -> dict[str, any]:
    """Renders the form fields for adding a new plant and returns the data."""
    return {
        "plant_name": st.text_input("Plant Name*"),
        "origin": st.text_input("Origin"),
        "growth_rate": st.text_input("Growth Rate"),
        "height_cm": st.text_input("Height (cm)"),
        "light_demand": st.text_input("Light Demand"),
        "co2_demand": st.text_input("CO2 Demand"),
        "thumbnail_url": st.text_input("Image URL (optional)")
    }

def plant_inventory_tab(key_prefix: str = "") -> None:
    """
    Renders the "Aquarium Plant Inventory" tab for the AquaLog application.
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        tank_repo = TankRepository()
        plant_repo = PlantRepository()
        owned_plant_repo = OwnedPlantRepository()

        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🌿 Aquarium Plant Inventory — {tank_name}")

        render_inventory_search("plant", plant_repo, owned_plant_repo, tid, _display_plant_details, key_prefix)
        render_add_new_item_form("plant", plant_repo, _plant_form_fields, key_prefix)

        st.write("---")
        st.subheader(f'🌱 Plants in {tank_name}')
        owned = owned_plant_repo.fetch_for_tank(tid)

        if owned.empty:
            st.info(f"No plants in {tank_name}. Use the search above to add some.")
        else:
            for _, row in owned.iterrows():
                with st.container(border=True):
                    cols = st.columns([1, 4, 1])
                    pid = row['plant_id']
                    _display_plant_details(row)

                    if cols[2].button('🗑️', key=f'{key_prefix}del_owned_plant_{pid}'):
                        owned_plant_repo.remove_from_tank(pid, tid)
                        st.toast(f"🗑️ Removed {row['display_name']} from {tank_name}")
                        st.rerun()
                    st.divider()
    except Exception as e:
        st.error(f"An error occurred in the plant inventory tab: {e}")