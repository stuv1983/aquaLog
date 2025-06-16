"""
tabs/plant_inventory_tab.py – fully multi‑tank aware 🌿

Manage your aquarium plant inventory per tank.
"""

import pandas as pd
import streamlit as st
import numpy as np

from aqualog_db.legacy import fetch_all_tanks
from aqualog_db.connection import get_connection
from utils import show_toast

def _ensure_owned_plants_schema():
    """Ensure the owned_plants table has the required schema."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(owned_plants);")
        cols = {row[1] for row in cur.fetchall()}
        
        if 'tank_id' not in cols:
            cur.execute("ALTER TABLE owned_plants ADD COLUMN tank_id INTEGER NOT NULL DEFAULT 1")
        
        if 'common_name' not in cols:
            cur.execute("ALTER TABLE owned_plants ADD COLUMN common_name TEXT DEFAULT ''")
        conn.commit()

def plant_inventory_tab(key_prefix=""):
    """Manage per-tank plant inventory."""
    try:
        tid = st.session_state.get('tank_id', 1)
        _ensure_owned_plants_schema()

        tanks = fetch_all_tanks()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🌿 Aquarium Plant Inventory — {tank_name}")

        # 1. Load master plants from database
        with get_connection() as conn:
            master = pd.read_sql_query("""
                SELECT * FROM plants ORDER BY plant_name COLLATE NOCASE
            """, conn)

        # --- RESTORED: Search master plant list ---
        st.subheader('🔍 Search Plant Database')
        query = st.text_input('Search all plants to add to your inventory...', key=f'{key_prefix}plant_search').strip().lower()

        if query:
            search_cols = [col for col in master.columns if master[col].dtype == 'object']
            search_series = master[search_cols].astype(str).agg(' '.join, axis=1).str.lower()
            filtered = master[search_series.str.contains(query, na=False)]
            
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
                        
                        if cols[2].button('➕ Add', key=f'{key_prefix}add_{pid}'):
                            try:
                                with get_connection() as conn:
                                    conn.execute("""
                                        INSERT INTO owned_plants (plant_id, common_name, tank_id)
                                        VALUES (?, ?, ?) ON CONFLICT(plant_id, tank_id) DO NOTHING
                                    """, (pid, name, tid))
                                    conn.commit()
                                show_toast('✅ Added', f'{name} added to {tank_name}')
                                st.rerun()
                            except Exception as e:
                                st.error(f"Couldn't add plant: {str(e)}")
        st.write("---")
        # --- END OF RESTORED SECTION ---

        # 2. List owned plants in the current tank
        st.subheader(f'🌱 Plants in {tank_name}')
        with get_connection() as conn:
            owned = pd.read_sql_query("""
                SELECT 
                    p.*,
                    COALESCE(NULLIF(o.common_name, ''), p.plant_name) AS display_name
                FROM owned_plants o
                JOIN plants p ON o.plant_id = p.plant_id
                WHERE o.tank_id = ?
                ORDER BY display_name COLLATE NOCASE
            """, conn, params=(tid,))

        if owned.empty:
            st.info(f"No plants in {tank_name}. Use the search above to add some.")
        else:
            search_term_owned = st.text_input('🔍 Filter your plants', key=f'{key_prefix}plant_filter_owned').strip().lower()
            if search_term_owned:
                search_cols_owned = ["display_name", "origin", "growth_rate"]
                search_series_owned = owned[search_cols_owned].astype(str).agg(' '.join, axis=1).str.lower()
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
                            with get_connection() as conn:
                                conn.execute("DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?", (pid, tid))
                                conn.commit()
                            show_toast('🗑️ Removed', f'{name} removed')
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't remove plant: {str(e)}")
                    st.divider()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please try refreshing the page. If the problem persists, contact support.")