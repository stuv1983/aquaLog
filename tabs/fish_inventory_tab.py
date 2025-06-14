"""
tabs/fish_inventory_tab.py – multi-tank aware 🐟
Renders fish catalogue and owned fish, scoped to selected tank via
`st.session_state['tank_id']`. Master list loaded entirely into a DataFrame
so searches across *all* columns (common_name, scientific_name, origin,
numeric ranges, etc.) work reliably, regardless of schema variations.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ——— Refactored DB imports ———
from aqualog_db.legacy import fetch_all_tanks
from aqualog_db.connection import get_connection
from utils import show_toast

# ─────────────────────────────────────────────────────────────────────────────
# Helper: ensure owned_fish has tank_id
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _ensure_owned_fish_schema() -> None:
    """Add tank_id column to owned_fish if it’s missing."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(owned_fish);")
        cols = {r[1] for r in cur.fetchall()}
        if "tank_id" not in cols:
            cur.execute(
                "ALTER TABLE owned_fish ADD COLUMN tank_id INTEGER DEFAULT 1;"
            )
            conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Main renderer
# ─────────────────────────────────────────────────────────────────────────────
def fish_inventory_tab() -> None:
    """Render the Fish Inventory tab for the active tank."""
    _ensure_owned_fish_schema()

    tank_id = st.session_state.get("tank_id", 1)
    tanks = fetch_all_tanks()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")

    st.header(f"🐟 Aquarium Fish Inventory — {tank_name}")

    # ── Load full master fish table ──────────────────────────────────────────
    with get_connection() as conn:
        master_df = pd.read_sql_query("SELECT rowid AS fish_id, * FROM fish;", conn)

    # Normalize common/scientific name columns across different CSV schemas
    if "common_name" not in master_df.columns or master_df["common_name"].eq("").all():
        master_df["common_name"] = master_df.get("name_english", "")
    if "scientific_name" not in master_df.columns or master_df["scientific_name"].eq("").all():
        master_df["scientific_name"] = master_df.get("name_latin", "")

    master_df = master_df.drop(columns=[c for c in ("name_english", "name_latin") if c in master_df.columns])

    # ─── Search master list ──────────────────────────────────────────────────
    st.subheader("🔍 Search All Fish (to Add)")
    term = st.text_input(
        "Type any term (name, origin, pH, temp…) → press Enter",
        key="search_master_fish",
    ).strip().lower()

    if term:
        mask = master_df.drop(columns=["fish_id"]).apply(
            lambda row: any(term in str(v).lower() for v in row.values), axis=1
        )
        search_df = master_df[mask]
        if search_df.empty:
            st.info("No matching fish found.")
        else:
            for _, row in search_df.iterrows():
                fid = row["fish_id"]
                cn = row.get("common_name") or row.get("scientific_name") or "(Unnamed)"

                col1, col2 = st.columns([1, 3], gap="small")
                with col1:
                    img_url = row.get("image_url")
                    img = img_url or f"https://selectyourfish.com/webps1/{fid}.webp"
                    st.image(img, width=80)

                with col2:
                    st.markdown(f"### {cn}")
                    sci = row.get("scientific_name", "")
                    if sci and sci != cn:
                        st.write(f"**Scientific Name:** {sci}")

                    for field in [
                        "origin", "phmin", "phmax", "temperature_min",
                        "temperature_max", "cm_max", "swim", "tank_size_liter",
                    ]:
                        val = row.get(field)
                        if pd.notna(val) and val != "":
                            lbl = field.replace("_", " ").title()
                            st.write(f"**{lbl}:** {val}")

                    if st.button(f"➕ Add {cn}", key=f"add_{fid}_{tank_id}"):
                        with get_connection() as conn2:
                            conn2.execute(
                                "INSERT OR IGNORE INTO owned_fish (fish_id, common_name, tank_id) VALUES (?, ?, ?);",
                                (fid, cn, tank_id),
                            )
                            conn2.commit()
                        show_toast("✅ Added", f"{cn} added to {tank_name}")

            st.markdown("---")
    else:
        st.info("Enter a search term to find fish.")

    # ─── Owned fish list ─────────────────────────────────────────────────────
    st.subheader(f"🐠 My Owned Fish — {tank_name}")
    with get_connection() as conn:
        owned = pd.read_sql_query(
            "SELECT o.fish_id, o.common_name, f.* "
            "FROM owned_fish o "
            "JOIN fish f ON o.fish_id = f.rowid "
            "WHERE o.tank_id = ?;",
            conn,
            params=(tank_id,),
        )

    if owned.empty:
        st.info("No fish added to this tank yet.")
        return

    # Sub-search in owned list
    term2 = st.text_input("🔍 Search your owned fish", key="search_owned_fish").strip().lower()
    if term2:
        mask2 = owned.drop(columns=["fish_id", "common_name"]).apply(
            lambda row: any(term2 in str(v).lower() for v in row.values), axis=1
        )
        owned = owned[mask2]
        if owned.empty:
            st.info("No owned fish match your search.")
            return

    swim_map = {1: "Bottom", 2: "Mid", 3: "Top"}

    for _, row in owned.iterrows():
        fid = row["fish_id"]
        cn = row.get("common_name") or row.get("scientific_name", "") or "(Unnamed)"

        c1, c2, c3 = st.columns([1, 4, 1], gap="small")
        with c1:
            img = row.get("image_url")
            st.image(img, width=80) if pd.notna(img) and img else st.text("No image")

        with c2:
            st.markdown(f"### {cn}")
            sci = row.get("scientific_name", "")
            if sci and sci != cn:
                st.write(f"**Scientific Name:** {sci}")

            for field in [
                "origin", "phmin", "phmax", "temperature_min",
                "temperature_max", "cm_max", "swim", "tank_size_liter",
            ]:
                val = row.get(field)
                if pd.notna(val) and val != "":
                    lbl = field.replace("_", " ").title()
                    display = swim_map.get(val, val) if field == "swim" else val
                    st.write(f"**{lbl}:** {display}")

        if c3.button("🗑️ Remove", key=f"remove_{fid}_{tank_id}"):
            with get_connection() as conn3:
                conn3.execute(
                    "DELETE FROM owned_fish WHERE fish_id = ? AND tank_id = ?;",
                    (fid, tank_id),
                )
                conn3.commit()
            show_toast("🗑️ Removed", f"{cn} removed from {tank_name}")
