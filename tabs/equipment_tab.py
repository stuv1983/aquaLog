"""
tabs/equipment_tab.py – multi‑tank aware ⚙️
Equipment inventory tab.  Users can:
  • add a piece of equipment (name, category, purchase date, notes)
  • view equipment belonging to the **selected tank**
  • bulk‑remove items.

The table now stores a `tank_id` column so every row belongs to one aquarium.
If the column is missing (first run on a legacy DB) we create it on‑the‑fly.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import date
import sqlite3

from db import get_connection
from utils import show_toast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Filters",
    "Air Pumps & Stones",
    "CO₂ Bottle",
    "Fertilizers",
    "Seachem Products",
]

def _ensure_equipment_schema() -> None:
    """Create equipment table if absent and add `tank_id` column if missing."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                category      TEXT    NOT NULL,
                purchase_date TEXT,
                notes         TEXT,
                tank_id       INTEGER DEFAULT 1
            );
            """
        )
        # add column if legacy
        cur.execute("PRAGMA table_info(equipment);")
        cols = {row[1] for row in cur.fetchall()}
        if "tank_id" not in cols:
            cur.execute("ALTER TABLE equipment ADD COLUMN tank_id INTEGER DEFAULT 1;")
        conn.commit()


def equipment_tab() -> None:
    """Render the Equipment inventory tab (scoped to selected tank)."""
    _ensure_equipment_schema()

    st.header("⚙️ Equipment Inventory")

    tank_id: int = st.session_state.get("tank_id", 1)

    # ───────────────────────── “Add New Equipment” ──────────────────────────
    with st.expander("➕ Add New Equipment"):
        new_name = st.text_input("Name (e.g. ‘Fluval FX6 Filter’)", key="eq_new_name")
        new_category = st.selectbox("Category", CATEGORIES, key="eq_new_category")
        new_purchase = st.date_input(
            "Purchase Date (optional)", value=date.today(), key="eq_new_purchase"
        )
        new_notes = st.text_area("Notes (optional)", key="eq_new_notes")

        if st.button("✅ Add Equipment", key="eq_add_btn"):
            if not new_name.strip():
                st.error("⚠️ Equipment name is required.")
            else:
                with get_connection() as conn:
                    try:
                        conn.execute(
                            """
                            INSERT INTO equipment (name, category, purchase_date, notes, tank_id)
                            VALUES (?,?,?,?,?);
                            """,
                            (
                                new_name.strip(),
                                new_category,
                                new_purchase.isoformat(),
                                new_notes.strip() or None,
                                tank_id,
                            ),
                        )
                        conn.commit()
                        show_toast("✅ Added", f"Added {new_name} to tank #{tank_id}.")
                        st.experimental_rerun()
                    except sqlite3.Error as e:
                        st.error(f"Failed to add equipment: {e}")

    st.markdown("---")

    # ───────────────────────── “My Equipment” list ──────────────────────────
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT equipment_id, name, category, purchase_date, notes
            FROM equipment
            WHERE tank_id = ?
            ORDER BY category, name COLLATE NOCASE;
            """,
            conn,
            params=(tank_id,),
        )

    if df.empty:
        st.info("No equipment recorded for this tank yet.")
        return

    st.subheader("🗄️ My Equipment")
    to_remove: list[int] = []

    for _, row in df.iterrows():
        eid = int(row["equipment_id"])
        label = f"{row['name']}  ({row['category']})"
        if st.checkbox(label, key=f"eq_remove_{eid}"):
            to_remove.append(eid)

        with st.expander(f"Details for: {row['name']}"):
            st.write(f"• **Category:** {row['category']}")
            if row["purchase_date"]:
                st.write(f"• **Purchased On:** {row['purchase_date']}")
            if row["notes"]:
                st.write("• **Notes:**")
                st.write(row["notes"])

    # Bulk delete
    if to_remove:
        if st.button("🗑️ Remove Selected", key="eq_remove_btn"):
            with get_connection() as conn:
                try:
                    conn.executemany(
                        "DELETE FROM equipment WHERE equipment_id = ? AND tank_id = ?;",
                        [(eid, tank_id) for eid in to_remove],
                    )
                    conn.commit()
                    show_toast("🗑️ Removed", f"Removed {len(to_remove)} item(s).")
                    st.experimental_rerun()
                except sqlite3.Error as e:
                    st.error(f"Error removing equipment: {e}")
