"""
tabs/cycle_tab.py – multi-tank aware 🔄
Manages the nitrogen-cycle tracker: start/complete/cancel cycles, progress
bar, trend charts and cycle notes.  All cycle data is tied to the active tank
via `st.session_state["tank_id"]`
"""

import datetime                        # For handling dates and computing elapsed days
from datetime import date              # Shortcut for today's date

import streamlit as st                 # Streamlit for UI components
import pandas as pd                    # Pandas for DataFrame operations
import altair as alt                   # Altair for charting trends

from db import (
    fetch_data,
    get_connection,
    start_cycle,
    get_active_cycle,
    complete_cycle,
    cancel_cycle,
    fetch_all_tanks,
)
from utils import is_mobile, show_out_of_range_banner, clean_numeric_df, translate, format_with_units
from config import SAFE_RANGES

def cycle_tab():
    """
    Render the "Tank Cycling" tab for the active, named tank.
    """
    # Determine active tank and name
    tank_id = st.session_state.get("tank_id", 1)
    tanks = fetch_all_tanks()
    tank_name = next((t['name'] for t in tanks if t['id'] == tank_id), f"Tank #{tank_id}")

    # Header with tank name
    st.header(f"🔄 {translate('Tank Cycling')} — {tank_name}")

    # Display any out-of-range warnings from the latest test
    show_out_of_range_banner("cycle")

    # Connect to the SQLite database
    conn = get_connection()
    c = conn.cursor()

    # Ensure `cycles` and `cycle_notes` tables exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            id             INTEGER PRIMARY KEY,
            start_date     TEXT    NOT NULL,
            completed_date TEXT
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS cycle_notes (
            id           INTEGER PRIMARY KEY,
            note_date    TEXT    NOT NULL,
            note_text    TEXT    NOT NULL
        );
    """)
    conn.commit()

    # Fetch the active (non-completed) cycle
    c.execute(
        "SELECT start_date, id FROM cycles WHERE completed_date IS NULL ORDER BY start_date DESC LIMIT 1;"
    )
    row = c.fetchone()  # (start_date_str, cycle_id) or None

    # Mobile layout
    if is_mobile():
        with st.expander(translate("Show Cycle Details"), expanded=bool(row)):
            if row:
                start_date = datetime.datetime.fromisoformat(row[0]).date()
                cycle_id = row[1]
                days_elapsed = (date.today() - start_date).days
                st.write(f"**{translate('Cycle started on')}:** {start_date} ({translate('Day')} {days_elapsed + 1})")
            else:
                start_date = None
                cycle_id = None
                days_elapsed = None
                st.info(translate(f"No active cycle for {tank_name}. Tap below to start one."))

            if st.button("🆕 " + translate("Start New 30-Day Cycle"), use_container_width=True):
                new_date = date.today().isoformat()
                c.execute("INSERT INTO cycles (start_date) VALUES (?);", (new_date,))
                conn.commit()
                st.success(f"{translate('Cycle started on')} {new_date}.")
                st.experimental_request_rerun()
                return

            if start_date:
                progress = min(max(days_elapsed / 30.0, 0), 1)
                st.progress(progress)
                st.write(f"{translate('Progress')}: {days_elapsed} / 30 {translate('days')}")

                c.execute(
                    "SELECT COUNT(*) FROM water_tests WHERE tank_id = ? AND date >= ?;",
                    (tank_id, start_date.isoformat(),)
                )
                test_count = c.fetchone()[0]
                st.write(f"{translate('Tests logged since start')}: {test_count}")

                df_cycle = fetch_data(start_date.isoformat(), date.today().isoformat(), tank_id)
                if not df_cycle.empty:
                    st.markdown("#### " + translate("Ammonia & Nitrite During Cycle"))
                    melt_df = df_cycle.melt(
                        id_vars=["date"],
                        value_vars=["ammonia", "nitrite"],
                        var_name="param",
                        value_name="value"
                    )
                    chart = (
                        alt.Chart(melt_df)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("date:T", title=translate("Date")),
                            y=alt.Y("value:Q", title=translate("Value")),
                            color=alt.Color("param:N", title=translate("Parameter")),
                            tooltip=["date:T", "param:N", "value:Q"],
                        )
                        .properties(height=250)
                    )
                    st.altair_chart(chart, use_container_width=True)

                st.markdown("---")
                st.subheader("📝 " + translate("Cycle Notes"))
                notes_df = pd.read_sql_query(
                    "SELECT * FROM cycle_notes ORDER BY note_date DESC", conn
                )
                if not notes_df.empty:
                    for _, note in notes_df.iterrows():
                        st.write(f"- **{note['note_date']}**: {note['note_text']}")
                else:
                    st.write(translate("No notes yet."))

                st.markdown("**" + translate("Add a New Note") + "**")
                note_text = st.text_input(translate("Note"), key="new_cycle_note")
                if st.button(translate("Save Note"), use_container_width=True):
                    note_date = date.today().isoformat()
                    c.execute(
                        "INSERT INTO cycle_notes (note_date, note_text) VALUES (?, ?);",
                        (note_date, note_text),
                    )
                    conn.commit()
                    st.success(translate("Note saved."))
                    st.experimental_request_rerun()
                    return

                if start_date:
                    df2 = clean_numeric_df(df_cycle)
                    peaks = {p: df2[p].max(skipna=True) for p in ('ammonia','nitrite')}
                    ready = all(peaks[p] < SAFE_RANGES[p][1] for p in peaks)
                    if ready and st.button("✔️ " + translate("Complete Cycle"), use_container_width=True):
                        complete_cycle(cycle_id)
                        st.success(translate("Cycle marked as complete!"))
                        st.experimental_request_rerun()
                        return
                    if not ready and st.button("❌ " + translate("Cancel Cycle"), use_container_width=True):
                        cancel_cycle(cycle_id)
                        st.warning(translate("Cycle canceled."))
                        st.experimental_request_rerun()
                        return

    # Desktop layout
    else:
        if row:
            start_date = datetime.datetime.fromisoformat(row[0]).date()
            cycle_id = row[1]
            days_elapsed = (date.today() - start_date).days
            st.write(f"**{translate('Cycle started on')}:** {start_date} ({translate('Day')} {days_elapsed + 1})")
        else:
            start_date = None
            cycle_id = None
            days_elapsed = None
            st.info(translate(f"No active cycle for {tank_name}. Click below to start one."))

        if st.button("🆕 " + translate("Start New 30-Day Cycle")):
            new_date = date.today().isoformat()
            c.execute("INSERT INTO cycles (start_date) VALUES (?);", (new_date,))
            conn.commit()
            st.success(f"{translate('Cycle started on')} {new_date}.")
            st.experimental_request_rerun()
            return

        if start_date:
            progress = min(max(days_elapsed / 30.0, 0), 1)
            st.progress(progress)
            st.write(f"{translate('Progress')}: {days_elapsed} / 30 {translate('days')}")

            c.execute(
                "SELECT COUNT(*) FROM water_tests WHERE tank_id = ? AND date >= ?;",
                (tank_id, start_date.isoformat(),)
            )
            test_count = c.fetchone()[0]
            st.write(f"{translate('Tests logged since start')}: {test_count}")

            df_cycle = fetch_data(start_date.isoformat(), date.today().isoformat(), tank_id)
            if not df_cycle.empty:
                st.markdown("#### " + translate("Ammonia & Nitrite During Cycle"))
                melt_df = df_cycle.melt(
                    id_vars=["date"],
                    value_vars=["ammonia", "nitrite"],
                    var_name="param",
                    value_name="value"
                )
                chart = (
                    alt.Chart(melt_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("date:T", title=translate("Date")),
                        y=alt.Y("value:Q", title=translate("Value")),
                        color=alt.Color("param:N", title=translate("Parameter")),
                        tooltip=["date:T", "param:N", "value:Q"],
                    )
                    .properties(height=250)
                )
                st.altair_chart(chart, use_container_width=True)

            st.markdown("---")
            st.subheader("📝 " + translate("Cycle Notes"))
            notes_df = pd.read_sql_query(
                "SELECT * FROM cycle_notes ORDER BY note_date DESC", conn
            )
            if not notes_df.empty:
                for _, note in notes_df.iterrows():
                    st.write(f"- **{note['note_date']}**: {note['note_text']}")
            else:
                st.write(translate("No notes yet."))

            st.markdown("**" + translate("Add a New Note") + "**")
            note_text = st.text_input(translate("Note"), key="new_cycle_note_desktop")
            if st.button(translate("Save Note")):
                note_date = date.today().isoformat()
                c.execute(
                    "INSERT INTO cycle_notes (note_date, note_text) VALUES (?, ?);",
                    (note_date, note_text),
                )
                conn.commit()
                st.success(translate("Note saved."))
                st.experimental_request_rerun()
                return

            if start_date:
                df2 = clean_numeric_df(df_cycle)
                peaks = {p: df2[p].max(skipna=True) for p in ('ammonia','nitrite')}
                ready = all(peaks[p] < SAFE_RANGES[p][1] for p in peaks)
                if ready and st.button("✔️ " + translate("Complete Cycle")):
                    complete_cycle(cycle_id)
                    st.success(translate("Cycle marked as complete!"))
                    st.experimental_request_rerun()
                    return
                if not ready and st.button("❌ " + translate("Cancel Cycle")):
                    cancel_cycle(cycle_id)
                    st.warning(translate("Cycle canceled."))
                    st.experimental_request_rerun()
                    return

    conn.close()
