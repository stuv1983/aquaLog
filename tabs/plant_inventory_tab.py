"""
tabs/plant_inventory_tab.py – fully multi‑tank aware 🌿

Manage your aquarium plant inventory per tank:
 1. Search the Tropica master list and add plants to the selected tank
 2. Manual “Add New Plant” expander to insert into master list
 3. View, search, and remove owned plants scoped by tank

New for v3.3.0:
 • Per‑tank `tank_id` support in owned_plants (auto-added on first run)
 • All reads/writes to owned_plants include `tank_id = st.session_state['tank_id']`

Updated: 2025-06-08 (v3.3.0)
"""

import pandas as pd
import streamlit as st

# ——— Refactored DB imports ———
from aqualog_db.legacy import fetch_all_tanks
from aqualog_db.base   import BaseRepository

from utils import show_toast

# ──────────────────────────────────────────────────────────────────────────
# Ensure schema: add tank_id to owned_plants if missing
# ──────────────────────────────────────────────────────────────────────────
def _ensure_owned_plants_schema():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(owned_plants);")
        cols = {row[1] for row in cur.fetchall()}
        if 'tank_id' not in cols:
            cur.execute(
                "ALTER TABLE owned_plants ADD COLUMN tank_id INTEGER DEFAULT 1"
            )
            conn.commit()

# ──────────────────────────────────────────────────────────────────────────
# Fuzzy match helper
# ──────────────────────────────────────────────────────────────────────────
SEARCH_COLS = [
    'plant_name', 'origin', 'growth_rate',
    'height_cm', 'light_demand', 'co2_demand'
]

def _matches(row: pd.Series, term: str) -> bool:
    term = term.lower()
    return any(
        isinstance(row.get(col, ''), str) and term in row[col].lower()
        for col in SEARCH_COLS
    )

# ──────────────────────────────────────────────────────────────────────────
# Main tab
# ──────────────────────────────────────────────────────────────────────────
def plant_inventory_tab():
    """Manage per-tank plant inventory."""
    # Active tank
    tid = st.session_state.get('tank_id', 1)
    _ensure_owned_plants_schema()

    # Resolve current tank name
    tanks = fetch_all_tanks()
    tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

    # Header with tank name
    st.header(f"🌿 Aquarium Plant Inventory — {tank_name}")

    # 1️⃣ Load master plants
    with get_connection() as conn:
        master = pd.read_sql_query(
            """
            SELECT
                plant_id,
                plant_name,
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
            """,
            conn
        )

    # 2️⃣ Search master list
    st.subheader('🔍 Search Plant Database')
    query = st.text_input(
        'Type part of a plant name and press Enter', key='plant_search'
    ).strip()

    if query:
        filtered = master[master.apply(lambda r: _matches(r, query), axis=1)]
        if filtered.empty:
            st.info('No matching plants found.')
        else:
            for _, row in filtered.iterrows():
                pid = row['plant_id']
                name = row['plant_name'] or '(no name)'
                c0, c1, c2 = st.columns([1, 4, 1])
                # Thumbnail
                thumb = row['thumbnail_url']
                if thumb:
                    c0.image(thumb, width=80)
                else:
                    c0.text('No image')
                # Details
                with c1:
                    st.markdown(f'### {name}')
                    for label, field, info in [
                        ('Origin', 'origin', 'origin_info'),
                        ('Growth Rate', 'growth_rate', 'growth_info'),
                        ('Height (cm)', 'height_cm', 'height_info'),
                        ('Light Demand', 'light_demand', 'light_info'),
                        ('CO₂ Demand', 'co2_demand', 'co2_info'),
                    ]:
                        if row[field]: st.write(f'**{label}:** {row[field]}')
                        if row[info]: st.write(f'*{row[info]}*')
                # Add button
                if c2.button('➕ Add', key=f'add_{pid}_{tid}'):
                    try:
                        with get_connection() as conn:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO owned_plants
                                    (plant_id, common_name, tank_id)
                                VALUES (?, ?, ?)
                                """,
                                (pid, name, tid)
                            )
                            conn.commit()
                        c2.success('Added!')
                        show_toast('✅ Added', f'{name} added to {tank_name}')
                    except Exception as e:
                        c2.error(f'Error: {e}')
            st.markdown('---')
    else:
        st.info('Enter a search term above to find plants.')

    # 3️⃣ Manual add new plant
    with st.expander('➕ Add a New Plant to Database'):
        new = {
            'plant_name':    st.text_input('Plant Name'),
            'origin':        st.text_input('Origin (optional)'),
            'origin_info':   st.text_input('Origin Info (optional)'),
            'growth_rate':   st.text_input('Growth Rate (optional)'),
            'growth_info':   st.text_input('Growth Info (optional)'),
            'height_cm':     st.text_input('Height cm (optional)'),
            'height_info':   st.text_input('Height Info (optional)'),
            'light_demand':  st.text_input('Light Demand (optional)'),
            'light_info':    st.text_input('Light Info (optional)'),
            'co2_demand':    st.text_input('CO₂ Demand (optional)'),
            'co2_info':      st.text_input('CO₂ Info (optional)'),
            'thumbnail_url': st.text_input('Thumbnail URL (optional)'),
        }
        if st.button('✅ Insert into Plants Table'):
            if not new['plant_name'].strip():
                st.error('Plant Name is required.')
            else:
                with get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO plants (
                            plant_name, origin, origin_info,
                            growth_rate, growth_info,
                            height_cm, height_info,
                            light_demand, light_info,
                            co2_demand, co2_info,
                            thumbnail_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(new.values())
                    )
                    conn.commit()
                st.success('Inserted! (search to add to a tank)')
    st.markdown('---')

    # 4️⃣ List owned plants
    st.subheader(f'🌱 My Owned Plants — {tank_name}')
    with get_connection() as conn:
        owned = pd.read_sql_query(
            """
            SELECT
                o.plant_id,
                o.common_name,
                p.*
            FROM owned_plants o
            JOIN plants p ON o.plant_id = p.plant_id
            WHERE o.tank_id = ?
            ORDER BY o.common_name COLLATE NOCASE
            """,
            conn,
            params=(tid,)
        )
    if owned.empty:
        st.info('You haven’t added any plants to this tank yet.')
        return
    search_owned = st.text_input('🔍 Search your owned plants', key='owned_search').strip().lower()
    if search_owned:
        owned = owned[owned.apply(lambda r: _matches(r, search_owned), axis=1)]
        if owned.empty:
            st.info('No owned plants match your search.')
            return
    for _, row in owned.iterrows():
        pid = row['plant_id']
        name = row['common_name'] or row.get('plant_name', '(no name)')
        c0, c1, c2 = st.columns([1, 4, 1])
        img = row.get('thumbnail_url', '')
        if img:
            c0.image(img, width=80)
        else:
            c0.text('No image')
        with c1:
            st.markdown(f'### {name}')
            for label, field, info in [
                ('Origin', 'origin', 'origin_info'),
                ('Growth Rate', 'growth_rate', 'growth_info'),
                ('Height (cm)', 'height_cm', 'height_info'),
                ('Light Demand', 'light_demand', 'light_info'),
                ('CO₂ Demand', 'co2_demand', 'co2_info'),
            ]:
                if row[field]: st.write(f'**{label}:** {row[field]}')
                if row[info]: st.write(f'*{row[info]}*')
        if c2.button('🗑️ Remove', key=f'remove_{pid}_{tid}'):
            with get_connection() as conn:
                conn.execute(
                    "DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?",
                    (pid, tid)
                )
                conn.commit()
            c2.warning('Removed')
            show_toast('🗑️ Removed', f'{name} removed from {tank_name}')
