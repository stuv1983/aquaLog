# tabs/fish_inventory_tab.py

"""
fish_inventory_tab.py – Fish & Fauna Inventory Management

Renders the "Fish" tab. Allows users to search a master database of fish, add
livestock to their tank's inventory, and add new, unlisted fish species to the
master database.
"""
import streamlit as st
import pandas as pd
import sqlite3
from aqualog_db.repositories import TankRepository, FishRepository, OwnedFishRepository
from utils import show_toast

def fish_inventory_tab(key_prefix=""):
    """Manage per-tank fish inventory."""
    try:
        tid = st.session_state.get('tank_id', 1)
        
        tank_repo = TankRepository()
        fish_repo = FishRepository()
        owned_fish_repo = OwnedFishRepository()
        
        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        # --- Search and Add Fish Section ---
        st.subheader('🔍 Search Fish Database')
        master = fish_repo.fetch_all()
        
        query = st.text_input('Search all fish to add to your inventory...', key=f'{key_prefix}fish_search').strip().lower()

        if query:
            search_cols = ['species_name', 'common_name', 'origin']
            search_series = master[search_cols].fillna('').apply(' '.join, axis=1).str.lower()
            filtered = master[search_series.str.contains(query, na=False)]
            
            if filtered.empty:
                st.info('No matching fish found in the database.')
            else:
                st.write("---")
                st.write("Search Results:")
                for _, row in filtered.iterrows():
                    with st.container():
                        fid = row['fish_id']
                        name = row['species_name']
                        common_name = row.get('common_name', '')
                        
                        cols = st.columns([1, 4, 1])
                        
                        if 'image_url' in row and row['image_url'] and str(row['image_url']).startswith('http'):
                            cols[0].image(row['image_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(f"{common_name} ({name})")
                            details = []
                            if pd.notna(row.get('phmin')) and pd.notna(row.get('phmax')):
                                details.append(f"**pH:** {row['phmin']} - {row['phmax']}")
                            if pd.notna(row.get('temperature_min')) and pd.notna(row.get('temperature_max')):
                                details.append(f"**Temp:** {row['temperature_min']}°C - {row['temperature_max']}°C")
                            st.write(" | ".join(details))

                        if cols[2].button('➕ Add to My Tank', key=f'{key_prefix}add_to_owned_{fid}'):
                            try:
                                owned_fish_repo.add_to_tank(fid, tid)
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Couldn't add fish: {str(e)}")
        
        # --- ADD NEW FISH TO DATABASE SECTION ---
        with st.expander("➕ Add New Fish to Database"):
            with st.form("new_fish_form", clear_on_submit=True):
                st.write("If a fish is not in the search results, you can add it to the master database here.")
                
                species_name = st.text_input("Species Name (Scientific)*", help="e.g., Ancistrus sp.")
                common_name = st.text_input("Common Name*", help="e.g., Bristlenose Pleco")
                origin = st.text_input("Origin", help="e.g., South America")
                
                c1, c2 = st.columns(2)
                phmin = c1.number_input("Min pH", value=6.5, step=0.1)
                phmax = c2.number_input("Max pH", value=7.5, step=0.1)
                
                c3, c4 = st.columns(2)
                temp_min = c3.number_input("Min Temp (°C)", value=22.0, step=0.5)
                temp_max = c4.number_input("Max Temp (°C)", value=28.0, step=0.5)
                
                tank_size = st.number_input("Min Tank Size (Liters)", value=75, step=5)
                image_url = st.text_input("Image URL (optional)")
                
                submitted = st.form_submit_button("💾 Save New Fish to Database")
                if submitted:
                    if not species_name or not common_name:
                        st.error("Species Name and Common Name are required.")
                    else:
                        try:
                            fish_data = {
                                "species_name": species_name,
                                "common_name": common_name,
                                "origin": origin,
                                "phmin": phmin,
                                "phmax": phmax,
                                "temperature_min": temp_min,
                                "temperature_max": temp_max,
                                "tank_size_liter": tank_size,
                                "image_url": image_url
                            }
                            fish_repo.add_fish(fish_data)
                            show_toast("✅ Success", f"{common_name} has been added to the master database.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                             st.error(f"A fish with the species name '{species_name}' may already exist.")
                        except Exception as e:
                            st.error(f"Could not save fish: {e}")
        st.write("---")

        # --- Owned Fish Section ---
        st.subheader(f'🐟 Fish in {tank_name}')
        owned = owned_fish_repo.fetch_for_tank_with_details(tid)
        
        if owned.empty:
            st.info(f"No fish recorded in {tank_name}. Use the search above to add some.")
        else:
            for _, row in owned.iterrows():
                with st.container():
                    owned_id = row['owned_fish_id']
                    name = row['species_name']
                    common_name = row.get('common_name', '')
                    
                    cols = st.columns([1, 4, 1])

                    if 'image_url' in row and row['image_url'] and str(row['image_url']).startswith('http'):
                        cols[0].image(row['image_url'], width=80)

                    with cols[1]:
                        st.subheader(f"{common_name} ({name})")
                        details = []
                        if pd.notna(row.get('phmin')) and pd.notna(row.get('phmax')):
                            details.append(f"**pH:** {row['phmin']}-{row['phmax']}")
                        if pd.notna(row.get('temperature_min')) and pd.notna(row.get('temperature_max')):
                            details.append(f"**Temp:** {row['temperature_min']}°C - {row['temperature_max']}°C")
                        if pd.notna(row.get('origin')):
                            details.append(f"**Origin:** {row['origin']}")
                        if pd.notna(row.get('tank_size_liter')):
                            details.append(f"**Min Tank:** {int(row['tank_size_liter'])}L")
                        st.write(" | ".join(details))
                    
                    if cols[2].button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                        try:
                            owned_fish_repo.remove_from_tank(owned_id)
                            show_toast('🗑️ Removed', f"{name} removed from {tank_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't remove fish: {str(e)}")
                    st.divider()

    except Exception as e:
        if "no such table: owned_fish" in str(e):
            st.info("The 'owned_fish' table hasn't been created yet. No owned fish to display.")
        else:
            st.error(f"An error occurred: {str(e)}")