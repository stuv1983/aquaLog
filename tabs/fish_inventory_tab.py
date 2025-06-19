# tabs/fish_inventory_tab.py

"""
fish_inventory_tab.py – Fish & Fauna Inventory Management

Renders the "Fish" tab. Allows users to search a master database of fish, add
livestock to their tank's inventory, and add new, unlisted fish species to the
master database. It also displays the current fish inventory for the selected tank.
"""
import streamlit as st
import pandas as pd
import sqlite3 # Imported for specific exception handling (IntegrityError)
from aqualog_db.repositories import TankRepository, FishRepository, OwnedFishRepository
from utils import show_toast

def fish_inventory_tab(key_prefix=""):
    """
    Renders the "Fish & Fauna Inventory" tab for the AquaLog application.

    This tab provides functionalities to:
    1. Search the master fish database for species to add to a tank.
    2. Add new fish species to the master database if they are not found.
    3. Display and manage the list of fish currently owned in the selected tank.

    Args:
        key_prefix: A string prefix for Streamlit widget keys to ensure uniqueness
                    when this tab might be rendered multiple times or dynamically.
    """
    try:
        # Get the currently selected tank ID from session state.
        tid = st.session_state.get('tank_id', 1)
        
        # Instantiate necessary repository classes for database operations.
        tank_repo = TankRepository()
        fish_repo = FishRepository()
        owned_fish_repo = OwnedFishRepository()
        
        # Get the name of the current tank for display purposes.
        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        # --- Search and Add Fish Section (from master database) ---
        st.subheader('🔍 Search Fish Database')
        master = fish_repo.fetch_all() # Load all fish from the master database
        
        # Text input for searching fish by species name, common name, or origin.
        query = st.text_input('Search all fish to add to your inventory...', key=f'{key_prefix}fish_search').strip().lower()

        if query:
            # Define columns to search within the master fish table.
            search_cols = ['species_name', 'common_name', 'origin']
            # Create a combined string for searching across multiple columns.
            search_series = master[search_cols].fillna('').apply(' '.join, axis=1).str.lower()
            # Filter the master DataFrame based on the search query.
            filtered = master[search_series.str.contains(query, na=False)]
            
            if filtered.empty:
                st.info('No matching fish found in the database.')
            else:
                st.write("---")
                st.write("Search Results:")
                # Iterate and display each filtered fish result.
                for _, row in filtered.iterrows():
                    with st.container(border=True): # Use a container for better visual grouping
                        fid = row['fish_id']
                        name = row['species_name']
                        common_name = row.get('common_name', '')
                        
                        cols = st.columns([1, 4, 1]) # Layout with 3 columns: image, details, button
                        
                        # Display fish image if URL is available.
                        if 'image_url' in row and row['image_url'] and str(row['image_url']).startswith('http'):
                            cols[0].image(row['image_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(f"{common_name} ({name})")
                            details = []
                            # Display pH and temperature ranges.
                            if pd.notna(row.get('phmin')) and pd.notna(row.get('phmax')):
                                details.append(f"**pH:** {row['phmin']} - {row['phmax']}")
                            if pd.notna(row.get('temperature_min')) and pd.notna(row.get('temperature_max')):
                                details.append(f"**Temp:** {row['temperature_min']:.1f}°C - {row['temperature_max']:.1f}°C")
                            st.write(" | ".join(details)) # Display details in a single line
                        
                        # Button to add the fish to the current tank's inventory.
                        if cols[2].button('➕ Add to My Tank', key=f'{key_prefix}add_to_owned_{fid}'):
                            try:
                                owned_fish_repo.add_to_tank(fid, tid)
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun() # Rerun to update the "Fish in My Tank" section
                            except Exception as e:
                                st.error(f"Couldn't add fish: {str(e)}")
        
        # --- ADD NEW FISH TO DATABASE SECTION ---
        # Collapsible expander for adding new fish to the master database.
        with st.expander("➕ Add New Fish to Database"):
            with st.form("new_fish_form", clear_on_submit=True):
                st.write("If a fish is not in the search results, you can add it to the master database here.")
                
                # Input fields for new fish details.
                species_name = st.text_input("Species Name (Scientific)*", help="e.g., Ancistrus sp.")
                common_name = st.text_input("Common Name*", help="e.g., Bristlenose Pleco")
                origin = st.text_input("Origin", help="e.g., South America")
                
                # pH range inputs in two columns.
                c1, c2 = st.columns(2)
                phmin = c1.number_input("Min pH", value=6.5, step=0.1)
                phmax = c2.number_input("Max pH", value=7.5, step=0.1)
                
                # Temperature range inputs in two columns.
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
                            # Package new fish data into a dictionary.
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
                            fish_repo.add_fish(fish_data) # Add to master database
                            show_toast("✅ Success", f"{common_name} has been added to the master database.")
                            st.rerun() # Rerun to refresh search results and owned fish list
                        except sqlite3.IntegrityError:
                             # Handle case where a fish with the same species name already exists.
                             st.error(f"A fish with the species name '{species_name}' may already exist.")
                        except Exception as e:
                            st.error(f"Could not save fish: {e}")
        st.write("---") # Separator
        
        # --- Owned Fish Section (fish in the current tank) ---
        st.subheader(f'🐟 Fish in {tank_name}')
        # Fetch all owned fish for the current tank, with master details.
        owned = owned_fish_repo.fetch_for_tank_with_details(tid)
        
        if owned.empty:
            st.info(f"No fish recorded in {tank_name}. Use the search above to add some.")
        else:
            # Iterate and display each owned fish.
            for _, row in owned.iterrows():
                with st.container(border=True):
                    owned_id = row['owned_fish_id'] # Unique ID for this specific owned instance
                    name = row['species_name']
                    common_name = row.get('common_name', '')
                    
                    cols = st.columns([1, 4, 1])
                    
                    # Display fish image if URL is available.
                    if 'image_url' in row and row['image_url'] and str(row['image_url']).startswith('http'):
                        cols[0].image(row['image_url'], width=80)
                    
                    with cols[1]:
                        st.subheader(f"{common_name} ({name})")
                        details = []
                        # Display various details from the master fish record.
                        if pd.notna(row.get('phmin')) and pd.notna(row.get('phmax')):
                            details.append(f"**pH:** {row['phmin']}-{row['phmax']}")
                        if pd.notna(row.get('temperature_min')) and pd.notna(row.get('temperature_max')):
                            details.append(f"**Temp:** {row['temperature_min']:.1f}°C - {row['temperature_max']:.1f}°C")
                        if pd.notna(row.get('origin')):
                            details.append(f"**Origin:** {row['origin']}")
                        if pd.notna(row.get('tank_size_liter')):
                            details.append(f"**Min Tank:** {int(row['tank_size_liter'])}L")
                        st.write(" | ".join(details))
                    
                    # Delete button for each owned fish.
                    if cols[2].button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                        try:
                            owned_fish_repo.remove_from_tank(owned_id)
                            show_toast('🗑️ Removed', f"{name} removed from {tank_name}")
                            st.rerun() # Rerun to update the list after deletion
                        except Exception as e:
                            st.error(f"Couldn't remove fish: {str(e)}")
                    st.divider() # Divider between owned fish entries

    except Exception as e:
        # Handle specific database error if 'owned_fish' table is not yet created.
        if "no such table: owned_fish" in str(e):
            st.info("The 'owned_fish' table hasn't been created yet. No owned fish to display. Add some fish to get started!")
        else:
            # Catch any other unexpected errors and display.
            st.error(f"An error occurred: {str(e)}")
            st.error("Please try refreshing the page. If the problem persists, contact support.")