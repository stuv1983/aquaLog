"""
tabs/cycle_tab.py – Water-change & maintenance history tab
----------------------------------------------------------

Displays the 10 most-recent maintenance-cycle records for the
selected tank.  Pulls data from the `maintenance_cycles` table
and aliases columns so downstream UI code can keep using
`date` and `type`.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection


def cycle_tab() -> None:
    """Render the Water-change / Maintenance Cycle tab."""
    st.header("🔄 Water Change & Maintenance Cycle")

    # ──────────────────────────────────────────────────────────────
    # Fetch the last 10 maintenance-cycle records
    # ──────────────────────────────────────────────────────────────
    with get_connection() as conn:
        cycles_df = pd.read_sql(
            """
            SELECT
                created_at       AS date,      -- alias real timestamp
                maintenance_type AS type,      -- alias real type
                notes
            FROM   maintenance_cycles
            ORDER  BY datetime(created_at) DESC
            LIMIT  10
            """,
            conn,
        )

    # ──────────────────────────────────────────────────────────────
    # UI – display or fallback message
    # ──────────────────────────────────────────────────────────────
    if cycles_df.empty:
        st.info("No cycle / maintenance data recorded yet.")
        return

    st.dataframe(
        cycles_df,
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn(format="YYYY-MM-DD HH:mm"),
            "type": st.column_config.TextColumn("Maintenance type"),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )
