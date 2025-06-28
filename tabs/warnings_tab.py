# tabs/warnings_tab.py

"""
warnings_tab.py – Water Quality Warnings

Renders the "Warnings" tab, which displays structured alerts and recommended
action plans. It highlights out-of-range parameters and fish compatibility
issues based on the latest water tests. Users can filter warnings by date
range and specific parameters.
"""

from __future__ import annotations
from typing import Any, List, Dict, TypedDict, Optional
from datetime import date, datetime # Corrected import: import datetime class

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose
from utils.localization import format_with_units
from utils.validation import is_out_of_range

# Define a list of valid water parameters that are consistently checked for warnings.
VALID_PARAMETERS: list[str] = ["ph", "ammonia", "nitrite", "nitrate", "temperature", "kh", "gh", "co2_indicator"]

# Define TypedDicts for structured type hinting of warning data
class WarningParamDetail(TypedDict):
    """Details for a single out-of-range parameter."""
    param: str
    value: Any

class WarningEntry(TypedDict, total=False):
    """Represents a single warning entry for a water test date."""
    date: str
    tank: str
    volume_l: Optional[float]
    low_warnings: List[WarningParamDetail]
    high_warnings: List[WarningParamDetail]
    fish_compatibility_warnings: List[str]

def _build_banner_details(param: str, value: float, low: float, high: float) -> str:
    """
    Constructs a formatted string detailing an out-of-range parameter and its
    associated action plan for display in warning banners or advice cards.
    """
    if value < low:
        plan = LOW_ACTION_PLANS.get(param, ["No plan available."])
        return (f"- **{param.upper()}**: Too low ({format_with_units(value, param)} < "
                f"{format_with_units(low, param)}); " + "; ".join(plan))
    
    plan = ACTION_PLANS.get(param, ["No plan available."])
    return (f"- **{param.upper()}**: Too high ({format_with_units(value, param)} > "
            f"{format_with_units(high, param)}); " + "; ".join(plan))


def show_parameter_advice(param: str, value: float) -> None:
    """
    Displays formatted advice for a single parameter based on whether its value
    is too low, too high, or within the safe range.
    """
    if param not in SAFE_RANGES:
        st.warning(f"Unknown parameter: {param}")
        return
        
    low, high = SAFE_RANGES[param]
    formatted_value = format_with_units(value, param)
    
    if value < low:
        with st.container(border=True):
            st.warning(f"⚠️ {param.upper()} is too LOW ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in LOW_ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    if value > high:
        with st.container(border=True):
            st.error(f"❗ {param.upper()} is too HIGH ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    st.success(
        f"✓ {param.upper()} ({formatted_value}) is within safe range "
        f"({format_with_units(low, param)}–{format_with_units(high, param)})",
        icon="✓"
    )


def warnings_tab(key_prefix: str = "") -> None:
    """
    Renders the "Water Quality Warnings" tab for the AquaLog application.
    """
    st.header("⚠️ Test Warnings for Current Tank")

    selected_tank_id = st.session_state.get("tank_id")
    if not selected_tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # --- Filter Controls ---
    with st.expander("🔍 Filter Warnings"):
        col1, col2 = st.columns(2)
        with col1:
            date_range: List[date] = st.date_input("Filter by date range", value=[], key=f"{key_prefix}warnings_date_range")
        with col2:
            filter_options: List[str] = ["All"] + VALID_PARAMETERS
            params_to_filter: List[str] = st.multiselect("Filter by parameter", options=filter_options, default=["All"], key=f"{key_prefix}warnings_param_filter")

    # --- Database Queries ---
    with get_connection() as conn:
        query_tests = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh, wt.co2_indicator "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ?"
        )
        query_params: List[Any] = [selected_tank_id]
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            query_tests += " AND date(wt.date) BETWEEN ? AND ?"
            query_params.extend([start_date.isoformat(), end_date.isoformat()])
        query_tests += " ORDER BY datetime(wt.date) DESC"
        
        filters_active: bool = bool(date_range) or (bool(params_to_filter) and "All" not in params_to_filter)
        if not filters_active:
            query_tests += " LIMIT 10"
        
        tests_df: pd.DataFrame = pd.read_sql(query_tests, conn, params=tuple(query_params))

        owned_fish_df: pd.DataFrame = pd.read_sql_query("""
            SELECT f.species_name, f.phmin, f.phmax, f.temperature_min, f.temperature_max
            FROM owned_fish of
            JOIN fish f ON of.fish_id = f.fish_id
            WHERE of.tank_id = ?
        """, conn, params=(selected_tank_id,)) # Use selected_tank_id here

    if tests_df.empty:
        st.info("No test data available for the selected tank or filters.")
        return

    # --- Warning Generation Logic ---
    warnings: List[WarningEntry] = []
    params_to_check: List[str] = params_to_filter if params_to_filter and "All" not in params_to_filter else VALID_PARAMETERS

    for _, row in tests_df.iterrows():
        low_warnings: List[WarningParamDetail] = []
        high_warnings: List[WarningParamDetail] = []
        fish_compatibility_warnings: List[str] = []

        test_date_time_obj = datetime.fromisoformat(row['date']) # Corrected usage here
        test_time_for_co2 = test_date_time_obj.time()

        for param in params_to_check:
            value = row.get(param)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            if is_out_of_range(
                param,
                value,
                tank_id=selected_tank_id, # Use selected_tank_id here
                ph=row.get("ph"),
                temp_c=row.get("temperature"),
                test_time=test_time_for_co2
            ):
                if param == "co2_indicator":
                    if "Blue" in value: low_warnings.append(WarningParamDetail(param=param, value=value))
                    elif "Yellow" in value: high_warnings.append(WarningParamDetail(param=param, value=value))
                elif pd.notna(value):
                    low, high = SAFE_RANGES.get(param, (0, 0))
                    if low is not None and float(value) < low: low_warnings.append(WarningParamDetail(param=param, value=float(value)))
                    if high is not None and float(value) > high: high_warnings.append(WarningParamDetail(param=param, value=float(value)))

        current_ph: Optional[float] = row.get("ph")
        current_temp: Optional[float] = row.get("temperature")
        if not owned_fish_df.empty:
            for _, fish in owned_fish_df.iterrows():
                if pd.notna(current_ph) and pd.notna(fish['phmin']) and not (fish['phmin'] <= current_ph <= fish['phmax']):
                    msg: str = f"**{fish['species_name']}**: Current pH of **{current_ph:.1f}** is outside its preferred range of {fish['phmin']:.1f} - {fish['phmax']:.1f}."
                    fish_compatibility_warnings.append(msg)
                if pd.notna(current_temp) and pd.notna(fish['temperature_min']) and not (fish['temperature_min'] <= current_temp <= fish['temperature_max']):
                    msg: str = f"**{fish['species_name']}**: Temp **{current_temp:.1f}°C** is outside its preferred range of {fish['temperature_min']:.1f}°C - {fish['temperature_max']:.1f}°C."
                    fish_compatibility_warnings.append(msg)

        if low_warnings or high_warnings or fish_compatibility_warnings:
            warnings.append(WarningEntry(
                date=row["date"],
                tank=row.get("tank_name", "Unknown"),
                volume_l=row.get("volume_l"),
                low_warnings=low_warnings,
                high_warnings=high_warnings,
                fish_compatibility_warnings=fish_compatibility_warnings
            ))

    if not warnings:
        st.success("No out-of-range parameters found for the selected criteria.")
        return

    # --- Display Logic ---
    st.subheader("Results")
    for warning in warnings:
        failing_params: List[str] = [item['param'].upper() for item in warning['low_warnings'] + warning['high_warnings']]
        if warning.get("fish_compatibility_warnings"):
            failing_params.append("FISH COMPATIBILITY")
        
        title: str = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(sorted(list(set(failing_params))))}"

        with st.expander(title):
            if warning.get("fish_compatibility_warnings"):
                with st.container(border=True):
                    st.subheader("🐠 Fish Compatibility Warnings")
                    for fish_warning in warning["fish_compatibility_warnings"]:
                        st.warning(fish_warning)
            
            if warning['low_warnings'] or warning['high_warnings']:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Out of Range Parameters")
                    st.caption(f"Tank: {warning['tank']}")
                    st.markdown("---")
                    for item in warning['low_warnings'] + warning['high_warnings']:
                        param, value = item['param'], item['value']
                        if param == 'co2_indicator':
                            st.metric(label=f"Parameter: {param.upper()}", value=str(value), delta="Should be Green", delta_color="off")
                        else:
                            safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                            if value is not None:
                                st.metric(label=f"Parameter: {param.upper()}", value=f"{float(value):.2f}", delta=f"Safe Range: {safe_low}–{safe_high}", delta_color="inverse")
                            else:
                                st.metric(label=f"Parameter: {param.upper()}", value="N/A", delta="No data", delta_color="off")
                with col2:
                    st.subheader("Recommended Actions")
                    volume_l: Optional[float] = warning.get("volume_l")
                    if not volume_l or volume_l <= 0:
                        st.info("Set tank volume in settings for dosing suggestions.")
                    
                    for low_item in warning['low_warnings']:
                        param, value = low_item['param'], low_item['value']
                        plan_list: List[str] = LOW_ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param not in ['co2_indicator'] and isinstance(value, (float, int)):
                            if param == 'kh':
                                safe_low_kh, _ = SAFE_RANGES.get('kh', (4.0, 8.0))
                                dose: float = calculate_alkaline_buffer_dose(volume_l, max(0, safe_low_kh - float(value)))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to raise KH.")
                            elif param == 'gh':
                                safe_low_gh, _ = SAFE_RANGES.get('gh', (6.0, 10.0))
                                dose: float = calculate_equilibrium_dose(volume_l, max(0, safe_low_gh - float(value)))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to raise GH.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---")
                    
                    for high_item in warning['high_warnings']:
                        param, value = high_item['param'], high_item['value']
                        plan_list: List[str] = ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param in ['ammonia', 'nitrite'] and isinstance(value, (float, int)):
                            dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system=True)
                            plan_list.insert(1, f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose_ml:.0f}ml / {dose_oz:.1f}oz** of FritzZyme 7.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---")