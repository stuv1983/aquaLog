# tabs/fish_inventory_tab.py (Updated)

"""
tabs/fish_inventory_tab.py – A robust tab for managing fish inventory.
"""
import streamlit as st
import pandas as pd
from aqualog_db.connection import get_connection
# 1. Import the repository instead of the legacy function
from aqualog_db.repositories import TankRepository
from utils import show_toast

def fish_inventory_tab(key_prefix=""):
    """
    Manage per-tank fish inventory.
    """
    try:
        tid = st.session_state.get('tank_id', 1)
        
        # 2. Instantiate the repository and call its method
        tank_repo = TankRepository()
        tanks = tank_repo.fetch_all()
        tank_name = next((t['name'] for t in tanks if t['id'] == tid), f"Tank #{tid}")

        st.header(f"🐠 Fish & Fauna Inventory — {tank_name}")

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
            # This is the important part for the delete button
            # NOTE: The user's file had a placeholder comment here. The actual logic to display
            # and delete fish is assumed to be implemented in a similar way to other tabs.
            # Based on the SQL query, the `owned_fish_id` is available for delete buttons.
            
            for _, row in owned.iterrows():
                owned_id = row['owned_fish_id'] # This uses the aliased column
                name = row['species_name']
                
                cols = st.columns([4, 1])
                with cols[0]:
                    st.write(name) # Placeholder for displaying fish info
                
                with cols[1]:
                    if st.button('🗑️', key=f"{key_prefix}del_owned_fish_{owned_id}"):
                        try:
                            with get_connection() as conn:
                                # FIX: Delete from the table using the correct primary key 'id'
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