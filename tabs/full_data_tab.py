"""
tabs/full_data_tab.py – multi‑tank aware 🗂️
“Full Water Test Data” – lets the user pick a date range, chart parameters,
view the raw table, download CSV, and import CSV *for the selected tank*.
All SQL queries now filter by `tank_id = st.session_state["tank_id"]`.
When importing CSV we back‑fill the same tank.
"""

import datetime
from datetime import date
import streamlit as st
import pandas as pd
import altair as alt

from db import fetch_data, get_connection
from utils import (
    is_mobile,
    show_out_of_range_banner,
    clean_numeric_df,
    multi_param_line_chart,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper – parse ISO or fuzzy date
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    for parser in (
        lambda s: datetime.datetime.fromisoformat(s).date(),
        lambda s: pd.to_datetime(s, errors="raise").date(),
    ):
        try:
            return parser(val)
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Tab renderer
# ─────────────────────────────────────────────────────────────────────────────

def full_data_tab() -> None:
    """Render the multi‑tank version of the “Full Data” tab."""
    tank_id = st.session_state.get("tank_id", 1)

    st.header("🗂️ Full Water Test Data")
    # Optional banner per‑tank (disabled by default to save vert space)
    # show_out_of_range_banner("full_data")

    # 1️⃣  Find min/max dates for *this* tank
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT MIN(date), MAX(date) FROM water_tests WHERE tank_id = ?;",
        (tank_id,),
    )
    min_str, max_str = cur.fetchone() or (None, None)
    conn.close()

    if not min_str:
        st.info("No data available for this tank.")
        return

    min_date = _parse_date(min_str)
    max_date = _parse_date(max_str)
    if min_date is None or max_date is None:
        st.error("Unable to parse date range from database.")
        return

    # 2️⃣  Date pickers
    if is_mobile():
        start_date = st.date_input("Start", min_value=min_date, max_value=max_date, value=min_date)
        end_date   = st.date_input("End",   min_value=min_date, max_value=max_date, value=max_date)
    else:
        start_date = st.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date)
        end_date   = st.date_input("End Date",   min_value=min_date, max_value=max_date, value=max_date)

    if start_date > end_date:
        st.error("Start Date must be on or before End Date.")
        return

    # 3️⃣  Fetch data for this tank
    df = fetch_data(start_date.isoformat(), end_date.isoformat(), tank_id)
    if df.empty:
        st.info("No data in the selected range.")
        return

    numeric_params = [c for c in df.columns if c not in ("date", "notes", "id", "tank_id")]

    # 4️⃣  Parameter selector
    st.markdown("#### Select Parameters to Chart")
    opts = ["All"] + numeric_params
    chosen = st.multiselect("", opts, default=["All"])
    params = numeric_params if "All" in chosen else [p for p in chosen if p in numeric_params]

    # 5️⃣  Layout (responsive)
    mobile = is_mobile()
    if mobile:
        _render_chart(df, params)
        st.divider()
        _render_table_and_download(df, params, start_date, end_date)
        _render_csv_import(df.columns, tank_id, key_suffix="mobile")
    else:
        col_chart, col_side = st.columns([2, 1])
        with col_chart:
            _render_chart(df, params)
        with col_side:
            _render_table_and_download(df, params, start_date, end_date)
            _render_csv_import(df.columns, tank_id, key_suffix="desk")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers to modularise UI blocks
# ─────────────────────────────────────────────────────────────────────────────

def _render_chart(df: pd.DataFrame, params: list[str]) -> None:
    st.markdown("#### Trend Chart")
    multi_param_line_chart(df, params)


def _render_table_and_download(df: pd.DataFrame, params: list[str], start_date, end_date) -> None:
    st.markdown("#### Table View")
    st.dataframe(df[["date"] + params], use_container_width=True)
    st.markdown("---")

    csv_bytes = df[["date"] + params + ["tank_id"]].to_csv(index=False).encode()
    st.download_button(
        "📥 Download Filtered Data",
        csv_bytes,
        file_name=f"water_tests_{start_date}_{end_date}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def _render_csv_import(all_cols: pd.Index, tank_id: int, key_suffix: str) -> None:
    if f"show_import_{key_suffix}" not in st.session_state:
        st.session_state[f"show_import_{key_suffix}"] = False

    if st.button("🔄 Import CSV", key=f"btn_import_{key_suffix}"):
        st.session_state[f"show_import_{key_suffix}"] = True

    if not st.session_state[f"show_import_{key_suffix}"]:
        return

    st.markdown("#### 📥 Import Past Results from CSV")
    st.write("Upload a CSV; entries with the same date for this tank will be replaced.")

    uploaded = st.file_uploader("Choose CSV", type=["csv"], key=f"csv_{key_suffix}")
    if uploaded is None:
        return

    try:
        df_csv = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        return

    df_csv.columns = df_csv.columns.str.strip().str.lower()
    if "date" not in df_csv.columns:
        st.error("CSV must include a 'date' column.")
        return

    # Keep only valid columns present in DB
    valid_cols = [c for c in df_csv.columns if c in all_cols]
    if not valid_cols:
        st.error("No CSV columns match the database schema.")
        return

    # Parse & normalise dates
    try:
        df_csv["date"] = pd.to_datetime(df_csv["date"], errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        st.error(f"Could not parse 'date' column: {e}")
        return

    if st.button("✅ Confirm Import", key=f"confirm_{key_suffix}"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Delete existing rows for this tank & matching dates
            for d in df_csv["date"].unique():
                cur.execute("DELETE FROM water_tests WHERE date = ? AND tank_id = ?;", (d, tank_id))

            # Build INSERT stmt
            insert_cols = valid_cols + ["tank_id"]
            ph = ", ".join("?" for _ in insert_cols)
            sql = f"INSERT INTO water_tests ({', '.join(insert_cols)}) VALUES ({ph});"

            for _, row in df_csv.iterrows():
                values = [row.get(c, None) for c in valid_cols] + [tank_id]
                cur.execute(sql, values)

            conn.commit()
            st.success(f"Imported {len(df_csv)} rows for tank #{tank_id}.")
        except Exception as e:
            conn.rollback()
            st.error(f"Error during import: {e}")
        finally:
            conn.close()
