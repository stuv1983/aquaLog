"""
Tabs/overview_tab.py – multi-tank dashboard 🏠

Overview tab rewritten to be **tank aware**. Every query filters by
`tank_id = st.session_state["tank_id"]` (fallback 1). Tank photos are stored
as `tank_images/tank_<id>.jpg`, so switching tanks shows the right picture.
Key sections:
1. Out-of-range banner
2. Photo upload/capture per tank
3. Summary KPIs (total tests, last test date, 7-day avg NO₃)
4. Latest test metrics with safe-range captions (includes GH)
5. Sparklines for recent trends (pH, Temp, Ammonia, Nitrite, NO₃, KH, GH)
6. PDF/XLSX report generator (selected date range, filtered by tank)
"""

import os
import io
from io import BytesIO
import datetime as dt

import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image

from db import get_connection, fetch_all_tanks
from aqualog_db.legacy import fetch_all_tanks
from utils import is_mobile, show_out_of_range_banner, translate, format_with_units
from config import SAFE_RANGES

# ─────────────────────────────────────────────────────────────────────────────
# Helper: get per-tank photo path
# ─────────────────────────────────────────────────────────────────────────────
def _photo_path(tank_id: int) -> str:
    images_dir = os.path.join(os.getcwd(), "tank_images")
    os.makedirs(images_dir, exist_ok=True)
    return os.path.join(images_dir, f"tank_{tank_id}.jpg")

# ─────────────────────────────────────────────────────────────────────────────
# PDF / Excel report helpers
# ─────────────────────────────────────────────────────────────────────────────
def _generate_pdf(df: pd.DataFrame, start: dt.date, end: dt.date, tank_name: str) -> bytes:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elems = [Paragraph(f"AquaLog Report: {tank_name} — {start} → {end}", styles["Title"]),
             Paragraph(" ", styles["Normal"])]

    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0077B6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elems.append(table)
    doc.build(elems)
    pdf = buf.getvalue()
    buf.close()
    return pdf


def _generate_xlsx(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Report", index=False)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# Main render function
# ─────────────────────────────────────────────────────────────────────────────
def overview_tab() -> None:
    # Determine active tank and name
    tank_id: int = st.session_state.get("tank_id", 1)
    tanks = fetch_all_tanks()
    tank_name = next((t["name"] for t in tanks if t["id"] == tank_id), f"Tank #{tank_id}")

    # Header
    st.header(f"🏠 Aquarium Overview — {tank_name}")

    # Out-of-range banner
    show_out_of_range_banner("overview")
    st.divider()

    # Photo section
    path = _photo_path(tank_id)
    if "tank_image" not in st.session_state:
        st.session_state["tank_image"] = None
    if st.session_state["tank_image"] is None and os.path.isfile(path):
        with open(path, "rb") as fh:
            st.session_state["tank_image"] = fh.read()

    if st.session_state["tank_image"] is None:
        if is_mobile():
            cam = st.camera_input(translate("Take a photo of this tank"))
            if cam:
                data = cam.read()
                st.session_state["tank_image"] = data
                with open(path, "wb") as fh:
                    fh.write(data)
        else:
            upl = st.file_uploader(translate("Upload a tank photo"), type=["png", "jpg", "jpeg"])
            if upl:
                data = upl.read()
                st.session_state["tank_image"] = data
                with open(path, "wb") as fh:
                    fh.write(data)

    if st.session_state["tank_image"]:
        img = Image.open(io.BytesIO(st.session_state["tank_image"]))
        st.subheader(translate("Current Tank Photo"))
        st.image(img, width=400)
        if st.button("🗑️ " + translate("Remove Photo")):
            st.session_state["tank_image"] = None
            if os.path.isfile(path):
                os.remove(path)
        st.divider()

    # Fetch data for this tank
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date",
            conn,
            params=(tank_id,),
        )
    finally:
        conn.close()

    if df.empty:
        st.info(translate("No water tests logged for this tank yet."))
        return

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    total_tests = len(df)
    last_date = df["date"].max().date()

    # 7-day avg nitrate (unchanged)
    seven_days_ago = (dt.datetime.utcnow() - dt.timedelta(days=7)).isoformat()
    conn2 = get_connection()
    try:
        res = conn2.execute(
            "SELECT AVG(nitrate) FROM water_tests WHERE tank_id = ? AND date >= ?",
            (tank_id, seven_days_ago),
        ).fetchone()
        nitrate_avg = res[0] if res and res[0] is not None else None
    finally:
        conn2.close()

    # KPI metrics
    col1, col2, col3 = st.columns(3)
    col1.metric(translate("Total Tests Logged"), total_tests)
    col2.metric(translate("Last Test Date"), str(last_date))
    col3.metric(
        translate("7-Day Avg NO₃"),
        f"{nitrate_avg:.1f}" if nitrate_avg is not None else "N/A"
    )
    st.divider()

    # Latest test snapshot (include GH)
    latest = df.sort_values("date").iloc[-1]
    metrics = [
        ("ph", "pH", None),
        ("temperature", "Temperature", "temp"),
        ("ammonia", "Ammonia", None),
        ("nitrite", "Nitrite", None),
        ("nitrate", "Nitrate", None),
        ("kh", "KH", None),
        ("gh", "GH", "hardness"),
    ]
    cols = st.columns(len(metrics))
    for col, (param, label, unit_key) in zip(cols, metrics):
        val = latest.get(param)
        if pd.isna(val):
            col.metric(translate(label), "N/A")
        else:
            lo, hi = SAFE_RANGES.get(param, (None, None))
            out = lo is not None and not (lo <= val <= hi)
            value_display = (
                format_with_units(val, unit_key)
                if unit_key else
                f"{val:.2f}"
            )
            col.metric(
                translate(label),
                value_display,
                delta=None,
                delta_color="inverse" if out else "normal"
            )
            if lo is not None:
                col.caption(f"{translate('Safe')}: {lo} – {hi}")
    st.divider()

    # Recent trends (sparkline for GH)
    st.subheader(translate("Recent Trends – last 20 readings"))
    trend_params = [
        ("ph", "pH", None),
        ("temperature", "Temperature", "temp"),
        ("ammonia", "Ammonia", None),
        ("nitrite", "Nitrite", None),
        ("nitrate", "Nitrate", None),
        ("kh", "KH", None),
        ("gh", "GH", "hardness"),
    ]
    for param, label, unit_key in trend_params:
        spark_df = df[["date", param]].dropna().tail(20)
        if spark_df.empty:
            continue
        trend_label = translate(label)
        base = alt.Chart(spark_df).encode(
            x=alt.X("date:T", title=translate("Date")),
            y=alt.Y(f"{param}:Q", title=trend_label),
            tooltip=["date:T", alt.Tooltip(f"{param}:Q", title=trend_label)]
        )
        line = base.mark_line()
        points = base.mark_point(size=60, color="white")
        chart = alt.layer(line, points).properties(height=80)
        st.altair_chart(chart, use_container_width=True)
    st.divider()

    # Report generator
    st.subheader("📑 " + translate("Generate Report"))
    start_date, end_date = st.date_input(
        translate("Select date range"),
        [df["date"].min().date(), df["date"].max().date()],
        key="report_dates",
    )
    if start_date > end_date:
        st.error(translate("Start date must be on or before end date"))
        return

    mask = (
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date))
    )
    report_df = df.loc[mask]

    sanitized = tank_name.replace(' ', '_')
    col_pdf, col_xlsx = st.columns(2)
    with col_pdf:
        if st.button("📄 " + translate("Download PDF")):
            pdf = _generate_pdf(report_df, start_date, end_date, tank_name)
            st.download_button(
                "📄 " + translate("Save PDF"),
                data=pdf,
                file_name=f"AquaLog_{sanitized}_{start_date}_{end_date}.pdf",
                mime="application/pdf",
            )
    with col_xlsx:
        if st.button("📊 " + translate("Download Excel")):
            xlsx = _generate_xlsx(report_df)
            st.download_button(
                "📊 " + translate("Save XLSX"),
                data=xlsx,
                file_name=f"AquaLog_{sanitized}_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
