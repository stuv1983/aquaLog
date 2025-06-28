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
import sqlite3 # Imported for specific exception handling (IntegrityError)
from typing import List # Ensure List is imported for clearer type hints

from aqualog_db.repositories import TankRepository, PlantRepository, OwnedPlantRepository
from aqualog_db.repositories.tank import TankRecord # Import TankRecord
from aqualog_db.repositories.plant import PlantRecord # Import PlantRecord

from utils import show_toast # Utility for displaying toast notifications

def plant_inventory_tab(key_prefix: str = "") -> None:
    """
    Renders the "Aquarium Plant Inventory" tab for the AquaLog application.

    This tab provides functionalities to:
    1.  **Search Plant Database:** Allows users to search a master catalog of aquatic
        plants by various attributes (e.g., name, origin, growth rate) and add
        found species to their selected tank's inventory.
    2.  **Add New Plant to Database:** Provides a form to add new, unlisted plant
        species directly to the master database.
    3.  **Plants in {Tank Name}:** Displays and allows management (e.g., removal) of
        the list of plants currently owned and associated with the selected tank.

    All operations within this tab are scoped to the `tank_id` stored in `st.session_state`.

    Args:
        key_prefix (str): A string prefix for Streamlit widget keys to ensure uniqueness
                          when this tab might be rendered multiple times or dynamically.
                          Defaults to an empty string.

    Returns:
        None: This function renders UI elements and does not return any value.

    Raises:
        Exception: Catches and displays general exceptions that might occur during
                   database operations or UI rendering within the tab, providing
                   user-friendly feedback. Specific database errors like
                   `sqlite3.IntegrityError` are handled for better user messages.
    """
    try:
        # Get the currently selected tank ID from session state.
        tid = st.session_state.get('tank_id', 1)

        # Instantiate necessary repository classes for database operations.
        tank_repo = TankRepository()
        plant_repo = PlantRepository()
        owned_plant_repo = OwnedPlantRepository()

        # Get the name of the current tank for display purposes.
        tanks: List[TankRecord] = tank_repo.fetch_all() # Explicitly type tanks
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🌿 Aquarium Plant Inventory — {tank_name}")

        # --- Search Master Plant List Section ---
        st.subheader('🔍 Search Plant Database')
        # Load all plants from the master database.
        master: pd.DataFrame = plant_repo.fetch_all() # Explicitly type master

        # Text input for searching plants by various attributes.
        query = st.text_input('Search all plants to add to your inventory...', key=f'{key_prefix}plant_search').strip().lower()

        if query:
            # Identify text columns for searching (all object-type columns).
            search_cols = [col for col in master.columns if master[col].dtype == 'object']
            
            if search_cols:
                # Concatenate relevant text columns for comprehensive searching.
                # Handle potential NaN values by filling with empty string before conversion.
                search_series = master[search_cols[0]].fillna('').astype(str)
                for col in search_cols[1:]:
                    search_series = search_series + ' ' + master[col].fillna('').astype(str)
                
                # Filter the master DataFrame based on the search query.
                filtered: pd.DataFrame = master[search_series.str.lower().str.contains(query, na=False)] # Explicitly type filtered
            else:
                filtered = pd.DataFrame() # Return empty if no searchable columns

            if filtered.empty:
                st.info('No matching plants found in the database.')
            else:
                st.write("---")
                st.write("Search Results:")
                # Iterate and display each filtered plant result.
                for _, row in filtered.iterrows():
                    with st.container(border=True): # Use a container for better visual grouping
                        pid = row['plant_id']
                        name = row['plant_name'] or 'Unnamed plant'
                        
                        # Layout with 3 columns: thumbnail, details, button.
                        cols = st.columns([1, 4, 1])
                        
                        # Display plant thumbnail if URL is available and valid.
                        if 'thumbnail_url' in row and row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                            cols[0].image(row['thumbnail_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(name)
                            # Exclude specific columns from general detail display.
                            exclude_cols = ['plant_id', 'plant_name', 'thumbnail_url']
                            # Display other relevant plant details.
                            for col_name in row.index:
                                if col_name not in exclude_cols and pd.notna(row[col_name]) and str(row[col_name]).strip():
                                    display_label = col_name.replace('_', ' ').title() # Format column name for display
                                    st.write(f"**{display_label}:** {row[col_name]}")
                        
                        # Button to add the plant to the current tank's inventory.
                        if cols[2].button('➕ Add to My Tank', key=f'{key_prefix}add_plant_to_owned_{pid}'):
                            try:
                                owned_plant_repo.add_to_tank(pid, tid, name) # Add to owned plants
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun() # Rerun to update the "Plants in My Tank" section
                            except Exception as e: # Catch any errors during addition to owned plants
                                st.error(f"Couldn't add plant: {str(e)}")
        
        # --- ADD NEW PLANT TO DATABASE SECTION ---
        # Collapsible expander for adding new plant species to the master database.
        with st.expander("➕ Add New Plant to Database"):
            with st.form("new_plant_form", clear_on_submit=True):
                st.write("If a plant is not in the search results, you can add it to the master database here.")
                
                # Input fields for new plant details.
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
                            # Package new plant data into a dictionary.
                            plant_data: PlantRecord = { # Explicitly type plant_data as PlantRecord
                                "plant_name": plant_name,
                                "origin": origin,
                                "growth_rate": growth_rate,
                                "height_cm": height_cm,
                                "light_demand": light_demand,
                                "co2_demand": co2_demand,
                                "thumbnail_url": thumbnail_url
                            }
                            plant_repo.add_plant(plant_data) # Add to master database
                            show_toast("✅ Success", f"{plant_name} has been added to the master database.")
                            st.rerun() # Rerun to refresh search results and owned plants list
                        except sqlite3.IntegrityError:
                            # Handle case where a plant with the same name might already exist (if unique constraint exists).
                            st.error(f"A plant with the name '{plant_name}' may already exist.")
                        except Exception as e: # Catch any other errors during saving new plant
                            st.error(f"Could not save plant: {e}")
        st.write("---") # Separator
        
        # --- List Owned Plants in the Current Tank Section ---
        st.subheader(f'🌱 Plants in {tank_name}')
        # Fetch all plants owned in the current tank, including display details.
        owned: pd.DataFrame = owned_plant_repo.fetch_for_tank(tid) # Explicitly type owned

        if owned.empty:
            st.info(f"No plants in {tank_name}. Use the search above to add some.")
        else:
            # Optional filter for the owned plants list.
            search_term_owned = st.text_input('🔍 Filter your plants', key=f'{key_prefix}plant_filter_owned').strip().lower()
            if search_term_owned:
                # Define columns to filter within owned plants list.
                search_cols_owned = ["display_name", "origin", "growth_rate"]
                # Create a combined string for filtering.
                search_series_owned = owned[search_cols_owned].fillna('').apply(' '.join, axis=1).str.lower()
                owned = owned[search_series_owned.str.contains(search_term_owned, na=False)]
                
                if owned.empty:
                    st.info('No plants match your filter.')

            # Iterate and display each owned plant.
            for _, row in owned.iterrows():
                with st.container(border=True):
                    cols = st.columns([1, 4, 1])
                    pid = row['plant_id']
                    name = row['display_name'] # Use the COALESCE'd display name
                    
                    # Display thumbnail if URL is available.
                    if 'thumbnail_url' in row and row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                        cols[0].image(row['thumbnail_url'], width=80)
                    
                    with cols[1]:
                        st.subheader(name)
                        # Exclude specific columns from display.
                        exclude_cols = ['plant_id', 'plant_name', 'display_name', 'thumbnail_url']
                        # Display other relevant details.
                        for col_name in row.index:
                            if col_name not in exclude_cols and pd.notna(row[col_name]) and str(row[col_name]).strip():
                                display_label = col_name.replace('_', ' ').title()
                                st.write(f"**{display_label}:** {row[col_name]}")
                    
                    # Delete button for each owned plant.
                    if cols[2].button('🗑️', key=f'{key_prefix}del_owned_plant_{pid}'):
                        try:
                            owned_plant_repo.remove_from_tank(pid, tid)
                            show_toast('🗑️ Removed', f'{name} removed from {tank_name}')
                            st.rerun() # Rerun to update the list after deletion
                        except Exception as e: # Catch any errors during removal from owned plants
                            st.error(f"Couldn't remove plant: {str(e)}")
                    st.divider() # Divider between owned plant entries

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please try refreshing the page. If the problem persists, contact support.")