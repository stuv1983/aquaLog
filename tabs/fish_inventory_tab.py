# tabs/fish_inventory_tab.py (Corrected and Complete)
"""
tabs/fish_inventory_tab.py – A robust tab for managing fish inventory.
"""
import streamlit as st
import pandas as pd
from aqualog_db.connection import get_connection
from aqualog_db.repositories import TankRepository
from utils import show_toast

def fish_inventory_tab(key_prefix=""):
    """
    Manage per-tank fish inventory.
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        
        tank_repo = TankRepository()
        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        # --- Search and Add Fish Section ---
        st.subheader('🔍 Search Fish Database')
        with get_connection() as conn:
            master = pd.read_sql_query("SELECT * FROM fish ORDER BY species_name COLLATE NOCASE", conn)
        
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

                        if cols[2].button('➕ Add', key=f'{key_prefix}add_fish_{fid}'):
                            try:
                                with get_connection() as conn:
                                    # Insert a new fish with quantity 1, or ignore if it already exists
                                    conn.execute("""
                                        INSERT INTO owned_fish (fish_id, tank_id, quantity)
                                        VALUES (?, ?, 1) ON CONFLICT(fish_id, tank_id) DO NOTHING
                                    """, (fid, tid))
                                    conn.commit()
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun() # Rerun to update the "owned" list below
                            except Exception as e:
                                st.error(f"Couldn't add fish: {str(e)}")
        st.write("---")


        # --- Owned Fish Section ---
        st.subheader(f'🐟 Fish in {tank_name}')
        with get_connection() as conn:
            owned = pd.read_sql_query("""
                SELECT
                    o.id as owned_fish_id, o.quantity, p.*
                FROM owned_fish o
                JOIN fish p ON o.fish_id = p.fish_id
                WHERE o.tank_id = ?
                ORDER BY p.species_name COLLATE NOCASE
            """, conn, params=(tid,))
        
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
                        # You can add more details here if needed
                    
                    if cols[2].button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                        try:
                            with get_connection() as conn:
                                conn.execute("DELETE FROM owned_fish WHERE id = ?", (owned_id,))
                                conn.commit()
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
