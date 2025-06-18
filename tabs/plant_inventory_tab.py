# tabs/plant_inventory_tab.py

"""
plant_inventory_tab.py – Plant Inventory Management

Renders the "Plants" tab. Allows users to search a master database of aquatic
plants, add plants to their specific tank's inventory, and add new, unlisted
plant species to the master database.
"""

import pandas as pd
import streamlit as st
import sqlite3

from aqualog_db.repositories import TankRepository, PlantRepository, OwnedPlantRepository
from utils import show_toast

def plant_inventory_tab(key_prefix=""):
    """Manage per-tank plant inventory."""
    try:
        tid = st.session_state.get('tank_id', 1)

        tank_repo = TankRepository()
        plant_repo = PlantRepository()
        owned_plant_repo = OwnedPlantRepository()

        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🌿 Aquarium Plant Inventory — {tank_name}")

        # 1. Load master plants from database
        master = plant_repo.fetch_all()

        # --- Search master plant list ---
        st.subheader('🔍 Search Plant Database')
        query = st.text_input('Search all plants to add to your inventory...', key=f'{key_prefix}plant_search').strip().lower()

        if query:
            search_cols = [col for col in master.columns if master[col].dtype == 'object']
            
            if search_cols:
                search_series = master[search_cols[0]].fillna('').astype(str)
                for col in search_cols[1:]:
                    search_series = search_series + ' ' + master[col].fillna('').astype(str)
                
                filtered = master[search_series.str.lower().str.contains(query, na=False)]
            else:
                filtered = pd.DataFrame()
            
            if filtered.empty:
                st.info('No matching plants found in the database.')
            else:
                st.write("---")
                st.write("Search Results:")
                for _, row in filtered.iterrows():
                    with st.container():
                        pid = row['plant_id']
                        name = row['plant_name'] or 'Unnamed plant'
                        cols = st.columns([1, 4, 1])
                        
                        if 'thumbnail_url' in row and row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                            cols[0].image(row['thumbnail_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(name)
                            exclude_cols = ['plant_id', 'plant_name', 'thumbnail_url']
                            for col_name in row.index:
                                if col_name not in exclude_cols and pd.notna(row[col_name]) and str(row[col_name]).strip():
                                    display_label = col_name.replace('_', ' ').title()
                                    st.write(f"**{display_label}:** {row[col_name]}")
                        
                        if cols[2].button('➕ Add to My Tank', key=f'{key_prefix}add_plant_to_owned_{pid}'):
                            try:
                                owned_plant_repo.add_to_tank(pid, tid, name)
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun()
                            except Exception as e:
                                st.error(f"Couldn't add plant: {str(e)}")
        
        # --- ADD NEW PLANT TO DATABASE SECTION ---
        with st.expander("➕ Add New Plant to Database"):
            with st.form("new_plant_form", clear_on_submit=True):
                st.write("If a plant is not in the search results, you can add it to the master database here.")
                
                plant_name = st.text_input("Plant Name*")
                origin = st.text_input("Origin")
                growth_rate = st.text_input("Growth Rate")
                height_cm = st.text_input("Height (cm)")
                light_demand = st.text_input("Light Demand")
                co2_demand = st.text_input("CO2 Demand")
                thumbnail_url = st.text_input("Image URL (optional)")
                
                submitted = st.form_submit_button("💾 Save New Plant to Database")
                if submitted:
                    if not plant_name:
                        st.error("Plant Name is required.")
                    else:
                        try:
                            plant_data = {
                                "plant_name": plant_name,
                                "origin": origin,
                                "growth_rate": growth_rate,
                                "height_cm": height_cm,
                                "light_demand": light_demand,
                                "co2_demand": co2_demand,
                                "thumbnail_url": thumbnail_url
                            }
                            plant_repo.add_plant(plant_data)
                            show_toast("✅ Success", f"{plant_name} has been added to the master database.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                             st.error(f"A plant with the name '{plant_name}' may already exist.")
                        except Exception as e:
                            st.error(f"Could not save plant: {e}")
        st.write("---")
        
        # 2. List owned plants in the current tank
        st.subheader(f'🌱 Plants in {tank_name}')
        owned = owned_plant_repo.fetch_for_tank(tid)

        if owned.empty:
            st.info(f"No plants in {tank_name}. Use the search above to add some.")
        else:
            search_term_owned = st.text_input('🔍 Filter your plants', key=f'{key_prefix}plant_filter_owned').strip().lower()
            if search_term_owned:
                search_cols_owned = ["display_name", "origin", "growth_rate"]
                search_series_owned = owned[search_cols_owned].fillna('').apply(' '.join, axis=1).str.lower()
                owned = owned[search_series_owned.str.contains(search_term_owned, na=False)]
                
                if owned.empty:
                    st.info('No plants match your filter.')

            for _, row in owned.iterrows():
                with st.container():
                    cols = st.columns([1, 4, 1])
                    pid = row['plant_id']
                    name = row['display_name']
                    
                    if 'thumbnail_url' in row and row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                        cols[0].image(row['thumbnail_url'], width=80)
                    
                    with cols[1]:
                        st.subheader(name)
                        exclude_cols = ['plant_id', 'plant_name', 'display_name', 'thumbnail_url']
                        for col_name in row.index:
                            if col_name not in exclude_cols and pd.notna(row[col_name]) and str(row[col_name]).strip():
                                display_label = col_name.replace('_', ' ').title()
                                st.write(f"**{display_label}:** {row[col_name]}")
                    
                    if cols[2].button('🗑️', key=f'{key_prefix}del_owned_plant_{pid}'):
                        try:
                            owned_plant_repo.remove_from_tank(pid, tid)
                            show_toast('🗑️ Removed', f'{name} removed')
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't remove plant: {str(e)}")
                    st.divider()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please try refreshing the page. If the problem persists, contact support.")