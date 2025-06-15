"""
tabs/plant_inventory_tab.py – fully multi‑tank aware 🌿

Manage your aquarium plant inventory per tank:
 1. Search the Tropica master list and add plants to the selected tank
 2. Manual "Add New Plant" expander to insert into master list
 3. View, search, and remove owned plants scoped by tank
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

        # 1️⃣ Load master plants from database
        with get_connection() as conn:
            master = pd.read_sql_query("""
                SELECT
                    plant_id,
                    COALESCE(plant_name, '') AS plant_name,
                    COALESCE(origin, '') AS origin,
                    COALESCE(origin_info, '') AS origin_info,
                    COALESCE(growth_rate, '') AS growth_rate,
                    COALESCE(growth_info, '') AS growth_info,
                    COALESCE(height_cm, '') AS height_cm,
                    COALESCE(height_info, '') AS height_info,
                    COALESCE(light_demand, '') AS light_demand,
                    COALESCE(light_info, '') AS light_info,
                    COALESCE(co2_demand, '') AS co2_demand,
                    COALESCE(co2_info, '') AS co2_info,
                    COALESCE(thumbnail_url, '') AS thumbnail_url
                FROM plants
                ORDER BY plant_name COLLATE NOCASE
            """, conn)

        # 2️⃣ Search master plant list
        st.subheader('🔍 Search Plant Database')
        query = st.text_input('Search plants...', key=f'{key_prefix}plant_search').strip().lower()

        if query:
            search_cols = ["plant_name", "origin", "growth_rate", "height_cm", "light_demand", "co2_demand"]
            search_series = master[search_cols].astype(str).agg(' '.join, axis=1).str.lower()
            filtered = master[search_series.str.contains(query, na=False)]
            
            if filtered.empty:
                st.info('No matching plants found.')
            else:
                for _, row in filtered.iterrows():
                    with st.container():
                        pid = row['plant_id']
                        name = row['plant_name'] or 'Unnamed plant'
                        cols = st.columns([1, 4, 1])
                        
                        if row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                            cols[0].image(row['thumbnail_url'], width=80)
                        
                        with cols[1]:
                            st.subheader(name)
                            info_pairs = [
                                ('Origin', 'origin', 'origin_info'),
                                ('Growth Rate', 'growth_rate', 'growth_info'),
                                ('Height', 'height_cm', 'height_info'),
                                ('Light', 'light_demand', 'light_info'),
                                ('CO₂', 'co2_demand', 'co2_info'),
                            ]
                            for label, val, desc in info_pairs:
                                if row[val]:
                                    st.write(f"**{label}:** {row[val]}")
                                if row[desc]:
                                    st.text(row[desc])
                        
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

        # 3️⃣ Manually add a new plant
        with st.expander('➕ Add New Plant to Database'):
            new_plant_values = {
                'plant_name': st.text_input('Scientific Name*', key=f'{key_prefix}new_name'),
                'origin': st.text_input('Origin', key=f'{key_prefix}new_origin'),
                'growth_rate': st.text_input('Growth Rate', key=f'{key_prefix}new_growth'),
                'height_cm': st.text_input('Height (cm)', key=f'{key_prefix}new_height'),
                'light_demand': st.text_input('Light Needs', key=f'{key_prefix}new_light'),
                'co2_demand': st.text_input('CO₂ Needs', key=f'{key_prefix}new_co2'),
                'thumbnail_url': st.text_input('Image URL', key=f'{key_prefix}new_image')
            }
            if st.button('Save New Plant', key=f'{key_prefix}save_new_plant'):
                if not new_plant_values['plant_name'].strip():
                    st.error('Scientific name is required')
                else:
                    try:
                        with get_connection() as conn:
                            conn.execute("""
                                INSERT INTO plants (plant_name, origin, growth_rate, height_cm, light_demand, co2_demand, thumbnail_url) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, tuple(new_plant_values.values()))
                            conn.commit()
                        st.success('Plant added to database!')
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Couldn't save plant: {str(e)}")

        # 4️⃣ List owned plants in the current tank
        st.subheader(f'🌱 Plants in {tank_name}')
        with get_connection() as conn:
            owned = pd.read_sql_query("""
                SELECT 
                    o.plant_id,
                    COALESCE(NULLIF(o.common_name, ''), p.plant_name) AS display_name,
                    p.*
                FROM owned_plants o
                JOIN plants p ON o.plant_id = p.plant_id
                WHERE o.tank_id = ?
                ORDER BY display_name COLLATE NOCASE
            """, conn, params=(tid,))

        if owned.empty:
            st.info(f"No plants in {tank_name}. Search above to add some.")
        else:
            search_term_owned = st.text_input('🔍 Filter your plants', key=f'{key_prefix}filter_owned').strip().lower()
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
                    
                    if row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                        cols[0].image(row['thumbnail_url'], width=80)
                    
                    with cols[1]:
                        st.subheader(name)
                        if row['origin']:
                            st.write(f"**Origin:** {row['origin']}")
                        if row['growth_rate']:
                            st.write(f"**Growth:** {row['growth_rate']}")
                    
                    if cols[2].button('🗑️', key=f'{key_prefix}del_{pid}'):
                        try:
                            with get_connection() as conn:
                                conn.execute("DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?", (pid, tid))
                                conn.commit()
                            show_toast('🗑️ Removed', f'{name} removed')
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Couldn't remove plant: {str(e)}")
                    st.divider()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please try refreshing the page. If the problem persists, contact support.")