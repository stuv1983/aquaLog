"""
tabs/maintenance_tab.py – multi-tank aware 🛠️

Records and displays maintenance entries (water changes, filter cleans, etc.)
for the selected tank via a dropdown. Logs are stored under the chosen tank
using `st.session_state["tank_id"]`.
"""

import streamlit as st
import pandas as pd
from datetime import date

# ——— Refactored DB imports ———
from aqualog_db.legacy import (
    save_maintenance,
    get_maintenance,
    delete_maintenance,
    fetch_all_tanks,
)


def maintenance_tab() -> None:
    """Maintenance Log tab (tank-aware; history shown under one expander)."""
    # ──────────────────────────────────────────────
    # Tank selector
    # ──────────────────────────────────────────────
    tanks = fetch_all_tanks()
    if not tanks:
        st.warning("No tanks found. Please add a tank first.")
        return

    tank_ids = [t["id"] for t in tanks]
    tank_names = {t["id"]: t["name"] for t in tanks}
    if "tank_id" not in st.session_state:
        st.session_state["tank_id"] = tank_ids[0]

    selected = st.selectbox(
        "Select Tank to Manage Maintenance",
        options=tank_ids,
        format_func=lambda tid: tank_names.get(tid, f"Tank #{tid}"),
        index=tank_ids.index(st.session_state["tank_id"]),
        key="tank_selector",
    )
    if selected != st.session_state["tank_id"]:
        st.session_state["tank_id"] = selected

    tank_id = st.session_state["tank_id"]
    tank_name = tank_names.get(tank_id, f"Tank #{tank_id}")

    # ──────────────────────────────────────────────
    # Header & Add Entry Form
    # ──────────────────────────────────────────────
    st.header(f"🛠️ Maintenance — {tank_name}")
    st.subheader("➕ Add New Maintenance Entry")
    with st.form("add_maintenance_form", clear_on_submit=True):
        date_in = st.date_input("Date", value=date.today())
        m_type = st.text_input("Type (e.g. Water Change, Filter Cleaning)")
        description = st.text_area("Description (optional)")
        volume = st.number_input(
            "Volume Changed (%, optional)", min_value=0.0, step=1.0, format="%.1f"
        )
        cost = st.number_input(
            "Cost ($, optional)", min_value=0.0, step=0.01, format="%.2f"
        )
        notes = st.text_area("Notes (optional)")
        next_due = st.date_input("Next Due (optional)", value=None)
        submitted = st.form_submit_button("Save Entry")

        if submitted:
            if not m_type:
                st.error("Maintenance type is required.")
            else:
                save_maintenance(
                    tank_id=tank_id,
                    date=date_in.isoformat(),
                    maintenance_type=m_type,
                    description=description or None,
                    volume_changed=volume if volume > 0 else None,
                    cost=cost if cost > 0 else None,
                    notes=notes or None,
                    next_due=next_due.isoformat() if next_due else None,
                )
                st.success(f"Entry added for {tank_name}.")
                st.experimental_rerun()

    st.markdown("---")

    # ──────────────────────────────────────────────
    # History (flat list under expander)
    # ──────────────────────────────────────────────
    with st.expander("🕒 View Maintenance History"):
        rows = get_maintenance(tank_id=tank_id) or []
        if not rows:
            st.info(f"No maintenance records found for {tank_name}.")
        else:
            for row in rows:
                st.markdown(f"**{row['date'][:10]} – {row['maintenance_type']} (#{row['id']})**")
                if row.get("description"):
                    st.write(f"- Description: {row['description']}")
                if row.get("volume_changed") is not None:
                    st.write(f"- Volume Changed: {row['volume_changed']} %")
                if row.get("cost") is not None:
                    st.write(f"- Cost: ${row['cost']:.2f}")
                if row.get("notes"):
                    st.write(f"- Notes: {row['notes']}")
                if row.get("next_due"):
                    st.write(f"- Next Due: {row['next_due'][:10]}")
                if st.button(
                    f"🗑️ Delete Record {row['id']}",
                    key=f"del_maint_{row['id']}"
                ):
                    delete_maintenance(row['id'])
                    st.warning("Record deleted.")
                    st.experimental_rerun()

