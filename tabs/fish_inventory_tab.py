# tabs/fish_inventory_tab.py

"""
fish_inventory_tab.py – Fish & Fauna Inventory Management

Renders the "Fish & Fauna" tab. Allows users to search a master database of
fish, add them to their tank's inventory, and add new species to the master
database. It also displays and allows management of the current fish inventory.
"""

import streamlit as st
import pandas as pd
from aqualog_db.repositories import TankRepository, FishRepository, OwnedFishRepository
from .inventory_tab_helpers import render_inventory_search, render_add_new_item_form

def _display_fish_details(row: pd.Series) -> None:
    """Displays the details for a fish."""
    common_name = row.get('common_name', '')
    name = row.get('species_name', 'Unnamed')
    st.subheader(f"{common_name} ({name})")
    details = []
    if pd.notna(row.get('phmin')) and pd.notna(row.get('phmax')):
        details.append(f"**pH:** {row['phmin']} - {row['phmax']}")
    if pd.notna(row.get('temperature_min')) and pd.notna(row.get('temperature_max')):
        details.append(f"**Temp:** {row['temperature_min']:.1f}°C - {row['temperature_max']:.1f}°C")
    st.write(" | ".join(details))

def _fish_form_fields() -> dict[str, any]:
    """Renders the form fields for adding a new fish and returns the data."""
    return {
        "species_name": st.text_input("Species Name (Scientific)*"),
        "common_name": st.text_input("Common Name*"),
        "origin": st.text_input("Origin"),
        "phmin": st.number_input("Min pH", value=6.5, step=0.1),
        "phmax": st.number_input("Max pH", value=7.5, step=0.1),
        "temperature_min": st.number_input("Min Temp (°C)", value=22.0, step=0.5),
        "temperature_max": st.number_input("Max Temp (°C)", value=28.0, step=0.5),
        "tank_size_liter": st.number_input("Min Tank Size (Liters)", value=75, step=5),
        "image_url": st.text_input("Image URL (optional)")
    }

def fish_inventory_tab(key_prefix: str = "") -> None:
    """
    Renders the "Fish & Fauna Inventory" tab for the AquaLog application.
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        tank_repo = TankRepository()
        fish_repo = FishRepository()
        owned_fish_repo = OwnedFishRepository()

        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        render_inventory_search("fish", fish_repo, owned_fish_repo, tid, _display_fish_details, key_prefix)
        render_add_new_item_form("fish", fish_repo, _fish_form_fields, key_prefix)

        st.write("---")
        st.subheader(f'🐟 Fish in {tank_name}')
        owned = owned_fish_repo.fetch_for_tank_with_details(tid)

        if owned.empty:
            st.info(f"No fish recorded in {tank_name}. Use the search above to add some.")
        else:
            for _, row in owned.iterrows():
                with st.container(border=True):
                    owned_id = row['owned_fish_id']
                    _display_fish_details(row)

                    if st.button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                        owned_fish_repo.remove_from_tank(owned_id)
                        st.toast(f"🗑️ Removed {row['common_name']} from {tank_name}")
                        st.rerun()
                    st.divider()
    except Exception as e:
        st.error(f"An error occurred in the fish inventory tab: {e}")