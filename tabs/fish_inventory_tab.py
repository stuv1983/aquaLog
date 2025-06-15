"""
tabs/fish_inventory_tab.py – A robust tab for managing fish inventory.
"""
import streamlit as st
import pandas as pd
from aqualog_db.connection import get_connection
from aqualog_db.legacy import fetch_all_tanks
from utils import show_toast

def fish_inventory_tab(key_prefix=""):
    """
    Manage per-tank fish inventory.
    
    Args:
        key_prefix (str): A string to prefix all widget keys to ensure uniqueness.
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        tanks = fetch_all_tanks()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        # 1. Load master fish list from database
        with get_connection() as conn:
            master_fish = pd.read_sql_query("""
                SELECT 
                    rowid AS fish_id,
                    COALESCE(name_latin, '') AS species_name,
                    COALESCE(name_english, '') AS common_name,
                    COALESCE(origin, '') AS origin,
                    COALESCE(cm_max, '') AS max_size_cm,
                    COALESCE(tank_size_liter, '') AS min_tank_size_l,
                    COALESCE(image_url, '') AS thumbnail_url
                FROM fish
                ORDER BY name_latin COLLATE NOCASE
            """, conn)

        # 2. Search master fish list
        st.subheader('🔍 Search Fish Database')
        st.write("Begin typing to search for fish to add to your tank.")
        query = st.text_input('Search fish...', key=f'{key_prefix}fish_search', label_visibility="collapsed").strip().lower()

        if query:
            search_cols = ['species_name', 'common_name', 'origin']
            mask = master_fish[search_cols].apply(
                lambda row: ' '.join(row.values.astype(str)).lower().find(query) != -1, 
                axis=1
            )
            filtered = master_fish[mask]

            if filtered.empty:
                st.info('No matching fish found.')
            else:
                st.subheader("Search Results")
                for _, row in filtered.iterrows():
                    with st.container():
                        fid = row['fish_id']
                        name = row['species_name']
                        common_name = row['common_name']
                        cols = st.columns([1, 4, 1])

                        if row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                            cols[0].image(row['thumbnail_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(name)
                            if common_name: st.write(f"({common_name})")
                            if row['origin']: st.write(f"**Origin:** {row['origin']}")
                            if row['max_size_cm']: st.write(f"**Max Size:** {row['max_size_cm']} cm")

                        if cols[2].button('➕ Add', key=f"{key_prefix}add_fish_{fid}"):
                            st.success(f"Added {name} to {tank_name}!")
                            st.rerun()
                        
                        st.divider()
        
        # 3. Add expander for adding new fish to the master list
        with st.expander("➕ Add New Fish to Database"):
            st.info("Functionality to add new fish to the master database can be built here.")

        # 4. List owned fish in the current tank
        st.subheader(f'🐟 Fish in {tank_name}')
        with get_connection() as conn:
            owned = pd.read_sql_query("""
                SELECT
                    o.owned_fish_id, o.quantity, p.*
                FROM owned_fish o
                JOIN fish p ON o.fish_id = p.rowid
                WHERE o.tank_id = ?
                ORDER BY p.name_latin COLLATE NOCASE
            """, conn, params=(tid,))
        
        if owned.empty:
            st.info(f"No fish recorded in {tank_name}.")
        else:
            search_term_owned = st.text_input('🔍 Filter your owned fish...', key=f'{key_prefix}filter_owned').strip().lower()
            
            owned_to_display = owned

            if search_term_owned:
                search_cols_owned = ['name_latin', 'name_english', 'origin']
                mask = owned[search_cols_owned].apply(
                    lambda row: ' '.join(row.values.astype(str)).lower().find(search_term_owned) != -1, 
                    axis=1
                )
                owned_to_display = owned[mask]

            if owned_to_display.empty:
                st.info('No owned fish match your filter.')
            else:
                for _, row in owned_to_display.iterrows():
                    with st.container():
                        cols = st.columns([1, 4, 1])
                        name = row['name_latin']
                        
                        if row['image_url'] and str(row['image_url']).startswith('http'):
                            cols[0].image(row['image_url'], width=80)

                        with cols[1]:
                            st.subheader(name)
                            if row['name_english']: st.write(f"({row['name_english']})")
                            if 'quantity' in row and row['quantity']: st.write(f"**Quantity:** {row['quantity']}")
                        
                        if cols[2].button('🗑️', key=f"{key_prefix}del_owned_fish_{row['owned_fish_id']}"):
                            st.rerun()
                        
                        st.divider()

    except Exception as e:
        if "no such table: owned_fish" in str(e):
            st.info("The 'owned_fish' table hasn't been created yet. No owned fish to display.")
        else:
            st.error(f"An error occurred: {str(e)}")