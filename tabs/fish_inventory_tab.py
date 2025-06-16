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
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        tanks = fetch_all_tanks()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

        # ... (Code for searching and adding fish is unchanged) ...

        # 4. List owned fish in the current tank
        st.subheader(f'🐟 Fish in {tank_name}')
        with get_connection() as conn:
            # FIX: Select o.id and alias it to owned_fish_id for use in the app
            owned = pd.read_sql_query("""
                SELECT
                    o.id as owned_fish_id, o.quantity, p.*
                FROM owned_fish o
                JOIN fish p ON o.fish_id = p.fish_id
                WHERE o.tank_id = ?
                ORDER BY p.species_name COLLATE NOCASE
            """, conn, params=(tid,))
        
        if owned.empty:
            st.info(f"No fish recorded in {tank_name}.")
        else:
            # ... (rest of the display logic is unchanged, it uses owned_fish_id from the query) ...
            
            # This is the important part for the delete button
            for _, row in owned_to_display.iterrows():
                # ...
                owned_id = row['owned_fish_id'] # This uses the aliased column
                # ...
                if cols[2].button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                    try:
                        with get_connection() as conn:
                            # FIX: Delete from the table using the correct primary key 'id'
                            conn.execute("DELETE FROM owned_fish WHERE id = ?", (owned_id,))
                            conn.commit()
                        show_toast('🗑️ Removed', f"{name} removed from {tank_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't remove fish: {str(e)}")
                # ...
    except Exception as e:
        if "no such table: owned_fish" in str(e):
            st.info("The 'owned_fish' table hasn't been created yet. No owned fish to display.")
        else:
            st.error(f"An error occurred: {str(e)}")