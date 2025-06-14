"""
tabs/maintenance_tab.py – multi-tank aware 🛠️

Records and displays maintenance entries (water changes, filter cleans, etc.)
for the selected tank via a dropdown. Now includes maintenance cycle management.
"""
import sqlite3
import streamlit as st
import pandas as pd
from datetime import date

# ——— Refactored DB imports ———
from aqualog_db.legacy import fetch_all_tanks
from aqualog_db.base   import BaseRepository
from aqualog_db.connection import get_connection

from utils import show_toast

print(">>> LOADING", __file__)
# ─────────────────────────────────────────────────────────────────────────────
# Local DB helpers for maintenance_log and maintenance_cycles
# ─────────────────────────────────────────────────────────────────────────────

def save_maintenance(
    *,
    tank_id: int,
    date: str,
    m_type: str,
    description: str | None,
    volume_changed: float | None,
    cost: float | None,
    notes: str | None,
    next_due: str | None,
    cycle_id: int | None = None
) -> None:
    """Insert a maintenance record for the given tank."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO maintenance_log (
                tank_id, date, maintenance_type, description,
                volume_changed, cost, notes, next_due, cycle_id
            ) VALUES (?,?,?,?,?,?,?,?,?);
            """,
            (
                tank_id,
                date,
                m_type.strip(),
                description.strip() if description else None,
                volume_changed,
                cost,
                notes.strip() if notes else None,
                next_due,
                cycle_id
            ),
        )
        conn.commit()

def get_maintenance(*, tank_id: int) -> list[dict]:
    """Return list of maintenance rows (latest first) for this tank."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT m.*, c.maintenance_type as cycle_name
              FROM maintenance_log m
              LEFT JOIN maintenance_cycles c ON m.cycle_id = c.id
             WHERE m.tank_id = ?
          ORDER BY m.date DESC, m.id DESC;
            """,
            (tank_id,),
        ).fetchall()
    return [dict(r) for r in rows]

def delete_maintenance(record_id: int) -> None:
    """Delete a maintenance row by id."""
    with get_connection() as conn:
        conn.execute("DELETE FROM maintenance_log WHERE id = ?;", (record_id,))
        conn.commit()

def fetch_maintenance_cycles(tank_id: int) -> list[dict]:
    """Return list of maintenance cycles for this tank."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * 
            FROM maintenance_cycles
            WHERE tank_id = ?
            ORDER BY is_active DESC, created_at DESC;
            """,
            (tank_id,),
        ).fetchall()
    return [dict(r) for r in rows]

def save_maintenance_cycle(
    *,
    tank_id: int,
    maintenance_type: str,
    frequency_days: int,
    description: str | None,
    notes: str | None,
    is_active: bool = True
) -> None:
    """Insert a maintenance cycle record."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO maintenance_cycles (
                tank_id, maintenance_type, frequency_days,
                description, notes, is_active
            ) VALUES (?,?,?,?,?,?);
            """,
            (
                tank_id,
                maintenance_type.strip(),
                frequency_days,
                description.strip() if description else None,
                notes.strip() if notes else None,
                is_active
            ),
        )
        conn.commit()

def delete_maintenance_cycle(cycle_id: int) -> None:
    """Delete a maintenance cycle by id."""
    with get_connection() as conn:
        conn.execute("DELETE FROM maintenance_cycles WHERE id = ?;", (cycle_id,))
        conn.commit()

def maintenance_tab() -> None:
    """Maintenance Log tab with cycle management and log history."""
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
    # Maintenance Cycles Management
    # ──────────────────────────────────────────────
    st.header(f"🛠️ Maintenance — {tank_name}")
    
    with st.expander("🔄 Manage Maintenance Cycles", expanded=False):
        st.subheader("Add New Maintenance Cycle")
        with st.form("add_cycle_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cycle_type = st.text_input("Type* (e.g. Weekly Water Change)")
                frequency = st.number_input("Frequency (days)*", min_value=1, step=1, value=7)
            with col2:
                is_active = st.checkbox("Active", value=True)
                
            cycle_desc = st.text_area("Description (optional)")
            cycle_notes = st.text_area("Notes (optional)")
            submitted = st.form_submit_button("💾 Save Cycle")

            if submitted:
                if not cycle_type:
                    show_toast("❌ Cycle type is required", icon="⚠️")
                else:
                    save_maintenance_cycle(
                        tank_id=tank_id,
                        maintenance_type=cycle_type,
                        frequency_days=frequency,
                        description=cycle_desc or None,
                        notes=cycle_notes or None,
                        is_active=is_active
                    )
                    show_toast("✅ Maintenance cycle added")
                    st.experimental_rerun()

        # Show existing cycles
        st.subheader("Existing Maintenance Cycles")
        cycles = fetch_maintenance_cycles(tank_id)
        if cycles:
            for cycle in cycles:
                with st.expander(f"{cycle['maintenance_type']} (every {cycle['frequency_days']} days)"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.markdown(f"**Status:** {'🟢 Active' if cycle['is_active'] else '⚪ Inactive'}")
                        if cycle.get('description'):
                            st.markdown(f"**Description:** {cycle['description']}")
                        if cycle.get('notes'):
                            st.markdown(f"**Notes:** {cycle['notes']}")
                        st.markdown(f"*Created: {cycle['created_at'][:10]}*")
                    with col2:
                        if st.button(
                            "🗑️ Delete",
                            key=f"del_cycle_{cycle['id']}",
                            help="Delete this maintenance cycle"
                        ):
                            delete_maintenance_cycle(cycle['id'])
                            show_toast("⚠️ Cycle deleted")
                            st.experimental_rerun()
        else:
            st.info("No maintenance cycles defined for this tank.")

    # ──────────────────────────────────────────────
    # Add Maintenance Entry Form
    # ──────────────────────────────────────────────
    st.subheader("➕ Add New Maintenance Entry")
    
    # Get active cycles for suggestions
    active_cycles = [c for c in fetch_maintenance_cycles(tank_id) if c['is_active']]
    selected_cycle = None
    
    with st.form("add_maintenance_form", clear_on_submit=True):
        # Date and Type selection
        col1, col2 = st.columns(2)
        with col1:
            date_in = st.date_input("Date*", value=date.today())
        
        with col2:
            if active_cycles:
                cycle_options = [{"label": "-- Custom Entry --", "value": None}] + \
                              [{"label": c['maintenance_type'], "value": c['id']} for c in active_cycles]
                selected_cycle = st.selectbox(
                    "Select from cycles (optional)",
                    options=cycle_options,
                    format_func=lambda x: x["label"]
                )
                if selected_cycle and selected_cycle["value"]:
                    m_type = next(c['maintenance_type'] for c in active_cycles 
                              if c['id'] == selected_cycle["value"])
                    st.text_input("Type*", value=m_type, disabled=True)
                else:
                    m_type = st.text_input("Type* (e.g. Water Change)")
            else:
                m_type = st.text_input("Type* (e.g. Water Change)")
        
        # Details
        description = st.text_area("Description (optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            volume = st.number_input(
                "Volume Changed (%)", 
                min_value=0.0, 
                max_value=100.0,
                step=1.0, 
                format="%.1f",
                value=0.0
            )
        with col2:
            cost = st.number_input(
                "Cost ($)", 
                min_value=0.0, 
                step=0.01, 
                format="%.2f",
                value=0.0
            )
        
        notes = st.text_area("Notes (optional)")
        
        # Auto-calculate next due if from cycle
        next_due = None
        if selected_cycle and selected_cycle["value"]:
            cycle = next(c for c in active_cycles if c['id'] == selected_cycle["value"])
            next_due = date_in + timedelta(days=cycle['frequency_days'])
            st.info(f"Next due will be automatically set to {next_due} based on cycle frequency")
        
        submitted = st.form_submit_button("💾 Save Entry")

        if submitted:
            if not m_type:
                show_toast("❌ Maintenance type is required", icon="⚠️")
            else:
                cycle_id = selected_cycle["value"] if selected_cycle else None
                save_maintenance(
                    tank_id=tank_id,
                    date=date_in.isoformat(),
                    m_type=m_type,
                    description=description or None,
                    volume_changed=volume if volume > 0 else None,
                    cost=cost if cost > 0 else None,
                    notes=notes or None,
                    next_due=next_due.isoformat() if next_due else None,
                    cycle_id=cycle_id
                )
                show_toast(f"✅ Entry added for {tank_name}")
                st.experimental_rerun()

    st.markdown("---")

    # ──────────────────────────────────────────────
    # Maintenance History
    # ──────────────────────────────────────────────
    with st.expander("🕒 View Maintenance History", expanded=True):
        rows = get_maintenance(tank_id=tank_id) or []
        if not rows:
            st.info(f"No maintenance records found for {tank_name}.")
        else:
            for row in rows:
                with st.container():
                    col1, col2 = st.columns([4,1])
                    with col1:
                        st.markdown(f"**{row['date'][:10]} – {row['maintenance_type']}**")
                        if row.get('cycle_name'):
                            st.caption(f"Part of cycle: {row['cycle_name']}")
                    with col2:
                        if st.button(
                            "🗑️",
                            key=f"del_maint_{row['id']}",
                            help="Delete this record"
                        ):
                            delete_maintenance(row['id'])
                            show_toast("⚠️ Record deleted")
                            st.experimental_rerun()
                    
                    if row.get("description"):
                        st.write(f"📝 {row['description']}")
                    
                    details = []
                    if row.get("volume_changed") is not None:
                        details.append(f"💧 {row['volume_changed']}% water")
                    if row.get("cost") is not None:
                        details.append(f"💵 ${row['cost']:.2f}")
                    if row.get("next_due"):
                        details.append(f"⏳ Next due: {row['next_due'][:10]}")
                    
                    if details:
                        st.write(" | ".join(details))
                    
                    if row.get("notes"):
                        st.write(f"📋 Notes: {row['notes']}")
                    
                    st.markdown("---")
