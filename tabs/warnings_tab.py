# tabs/warnings_tab.py

"""
warnings_tab.py – Water Quality Warnings

Renders the "Warnings" tab, which displays structured alerts and recommended
action plans. It highlights out-of-range parameters and fish compatibility
issues based on the latest water tests. Users can filter warnings by date
range and specific parameters.
"""

from __future__ import annotations
from typing import Any, List, Dict
from datetime import date

import pandas as pd
import streamlit as st

from aqualog_db.connection import get_connection
from config import SAFE_RANGES, ACTION_PLANS, LOW_ACTION_PLANS
from utils import calculate_alkaline_buffer_dose, calculate_equilibrium_dose, calculate_fritzzyme7_dose
from utils.localization import format_with_units # Added for formatting values with units

# Define a list of valid parameters that are checked for warnings.
VALID_PARAMETERS = ["ph", "ammonia", "nitrite", "nitrate", "temperature", "kh", "gh", "co2_indicator"]

def _build_banner_details(param: str, value: float, low: float, high: float) -> str:
    """
    Constructs a formatted string detailing an out-of-range parameter and its
    associated action plan for display in warning banners or advice cards.

    Args:
        param: The name of the parameter (e.g., "ph", "ammonia").
        value: The measured value of the parameter.
        low: The safe low threshold for the parameter.
        high: The safe high threshold for the parameter.

    Returns:
        A formatted string describing the warning and recommended actions.
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

    This function is typically used in a detailed view, showing specific action plans.

    Args:
        param: The name of the parameter.
        value: The measured value of the parameter.
    """
    if param not in SAFE_RANGES:
        st.warning(f"Unknown parameter: {param}")
        return
        
    low, high = SAFE_RANGES[param]
    formatted_value = format_with_units(value, param)
    
    if value < low:
        # Display warning for low parameters with advice.
        with st.container(border=True):
            st.warning(f"⚠️ {param.upper()} is too LOW ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in LOW_ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    if value > high:
        # Display error for high parameters with advice.
        with st.container(border=True):
            st.error(f"❗ {param.upper()} is too HIGH ({formatted_value})")
            st.caption(f"Safe range: {format_with_units(low, param)}–{format_with_units(high, param)}")
            for line in ACTION_PLANS.get(param, ["No plan available."]):
                st.write(f"• {line}")
        return
        
    # Display success message if parameter is within safe range.
    st.success(
        f"✓ {param.upper()} ({formatted_value}) is within safe range "
        f"({format_with_units(low, param)}–{format_with_units(high, param)})",
        icon="✓"
    )


def warnings_tab(key_prefix=""):
    """
    Renders the "Water Quality Warnings" tab for the AquaLog application.

    This tab allows users to view historical water test results that are
    out of range and provides fish compatibility warnings. It offers filters
    by date range and parameter.

    Args:
        key_prefix: A string prefix for Streamlit widget keys to ensure uniqueness.
    """
    st.header("⚠️ Test Warnings for Current Tank")

    # Retrieve the currently selected tank ID.
    tank_id = st.session_state.get("tank_id")
    if not tank_id:
        st.warning("Please select a tank to view its warnings.")
        return

    # --- Filter Controls ---
    # Allow users to filter warnings by date range and specific parameters.
    with st.expander("🔍 Filter Warnings"):
        col1, col2 = st.columns(2)
        with col1:
            # Date range input for filtering tests.
            date_range = st.date_input("Filter by date range", value=[], key=f"{key_prefix}warnings_date_range")
        with col2:
            # Multi-select for choosing specific parameters to filter.
            filter_options = ["All"] + VALID_PARAMETERS
            params_to_filter = st.multiselect("Filter by parameter", options=filter_options, default=["All"], key=f"{key_prefix}warnings_param_filter")

    # --- Database Queries ---
    with get_connection() as conn:
        # 1. Get water tests for the selected tank, potentially filtered by date.
        query_tests = (
            "SELECT wt.date, t.name AS tank_name, t.volume_l, wt.ammonia, wt.nitrate, wt.nitrite, "
            "wt.ph, wt.temperature, wt.kh, wt.gh, wt.co2_indicator "
            "FROM water_tests wt "
            "JOIN tanks t ON wt.tank_id = t.id "
            "WHERE wt.tank_id = ?"
        )
        query_params: List[Any] = [tank_id]
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            query_tests += " AND date(wt.date) BETWEEN ? AND ?"
            query_params.extend([start_date.isoformat(), end_date.isoformat()])
        query_tests += " ORDER BY datetime(wt.date) DESC"
        
        # Limit results if no filters are active to prevent loading too much data initially.
        filters_active = bool(date_range) or (bool(params_to_filter) and "All" not in params_to_filter)
        if not filters_active:
            query_tests += " LIMIT 10" # Show only latest 10 if no explicit filter
        
        tests_df = pd.read_sql(query_tests, conn, params=tuple(query_params))

        # 2. Get owned fish parameter ranges for the current tank to check compatibility.
        owned_fish_df = pd.read_sql_query("""
            SELECT f.species_name, f.phmin, f.phmax, f.temperature_min, f.temperature_max
            FROM owned_fish of
            JOIN fish f ON of.fish_id = f.fish_id
            WHERE of.tank_id = ?
        """, conn, params=(tank_id,))

    if tests_df.empty:
        st.info("No test data available for the selected tank or filters.")
        return

    # --- Warning Generation Logic ---
    warnings: List[Dict[str, Any]] = []
    # Determine which parameters to check based on user filter.
    params_to_check = params_to_filter if params_to_filter and "All" not in params_to_filter else VALID_PARAMETERS

    # Iterate through each water test record.
    for _, row in tests_df.iterrows():
        low_warnings, high_warnings, fish_compatibility_warnings = [], [], []

        # Check standard parameters against SAFE_RANGES.
        for param in params_to_check:
            value = row.get(param)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue # Skip if value is missing or empty string.

            if param == "co2_indicator":
                # Special handling for CO2 indicator which is categorical.
                if "Blue" in value: low_warnings.append({"param": param, "value": value})
                elif "Yellow" in value: high_warnings.append({"param": param, "value": value})
            elif pd.notna(value): # Ensure value is not NaN for numeric checks.
                low, high = SAFE_RANGES.get(param, (None, None))
                if low is not None and float(value) < low: low_warnings.append({"param": param, "value": float(value)})
                if high is not None and float(value) > high: high_warnings.append({"param": param, "value": float(value)})

        # NEW: Check pH and Temperature for each owned fish against current tank conditions.
        current_ph = row.get("ph")
        current_temp = row.get("temperature")
        if not owned_fish_df.empty:
            for _, fish in owned_fish_df.iterrows():
                # pH Compatibility Check.
                if pd.notna(current_ph) and pd.notna(fish['phmin']) and not (fish['phmin'] <= current_ph <= fish['phmax']):
                    msg = f"**{fish['species_name']}**: Current pH of **{current_ph:.1f}** is outside its preferred range of {fish['phmin']:.1f} - {fish['phmax']:.1f}."
                    fish_compatibility_warnings.append(msg)
                # Temperature Compatibility Check.
                if pd.notna(current_temp) and pd.notna(fish['temperature_min']) and not (fish['temperature_min'] <= current_temp <= fish['temperature_max']):
                    msg = f"**{fish['species_name']}**: Temp **{current_temp:.1f}°C** is outside its preferred range of {fish['temperature_min']:.1f}°C - {fish['temperature_max']:.1f}°C."
                    fish_compatibility_warnings.append(msg)

        # If any warnings are found for this test record, add it to the main warnings list.
        if low_warnings or high_warnings or fish_compatibility_warnings:
            warnings.append({
                "date": row["date"],
                "tank": row.get("tank_name", "Unknown"),
                "volume_l": row.get("volume_l"),
                "low_warnings": low_warnings,
                "high_warnings": high_warnings,
                "fish_compatibility_warnings": fish_compatibility_warnings
            })

    if not warnings:
        st.success("No out-of-range parameters found for the selected criteria.")
        return

    # --- Display Logic ---
    st.subheader("Results")
    # Iterate through and display each warning entry.
    for warning in warnings:
        failing_params = [item['param'].upper() for item in warning['low_warnings'] + warning['high_warnings']]
        if warning.get("fish_compatibility_warnings"):
            failing_params.append("FISH COMPATIBILITY")
        
        # Create a descriptive title for the expander.
        title = f"⚠️ {warning['date'][:10]} - Issues with: {', '.join(sorted(list(set(failing_params))))}"

        with st.expander(title):
            # Display Fish Compatibility Warnings First.
            if warning.get("fish_compatibility_warnings"):
                with st.container(border=True):
                    st.subheader("🐠 Fish Compatibility Warnings")
                    for fish_warning in warning["fish_compatibility_warnings"]:
                        st.warning(fish_warning)
            
            # Display standard parameter warnings and recommended actions.
            if warning['low_warnings'] or warning['high_warnings']:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Out of Range Parameters")
                    st.caption(f"Tank: {warning['tank']}")
                    st.markdown("---")
                    # Display metrics for each out-of-range parameter.
                    for item in warning['low_warnings'] + warning['high_warnings']:
                        param, value = item['param'], item['value']
                        if param == 'co2_indicator':
                            st.metric(label=f"Parameter: {param.upper()}", value=str(value), delta="Should be Green", delta_color="off")
                        else:
                            safe_low, safe_high = SAFE_RANGES.get(param, (0, 0))
                            st.metric(label=f"Parameter: {param.upper()}", value=f"{value:.2f}", delta=f"Safe Range: {safe_low}–{safe_high}", delta_color="inverse")
                with col2:
                    st.subheader("Recommended Actions")
                    volume_l = warning.get("volume_l")
                    if not volume_l or volume_l <= 0:
                        st.info("Set tank volume in settings for dosing suggestions.")
                    
                    # Provide action plans for low parameters, including dosing calculations.
                    for low_item in warning['low_warnings']:
                        param, value = low_item['param'], low_item['value']
                        plan_list = LOW_ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param not in ['co2_indicator']:
                            if param == 'kh':
                                safe_low_kh, _ = SAFE_RANGES.get('kh', (4.0, 8.0))
                                # Calculate dosage needed to reach safe low range.
                                dose = calculate_alkaline_buffer_dose(volume_l, max(0, safe_low_kh - value))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Alkaline Buffer to raise KH.")
                            elif param == 'gh':
                                safe_low_gh, _ = SAFE_RANGES.get('gh', (6.0, 10.0))
                                # Calculate dosage needed to reach safe low range.
                                dose = calculate_equilibrium_dose(volume_l, max(0, safe_low_gh - value))
                                plan_list.append(f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose:.2f}g** of Equilibrium to raise GH.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---") # Separator between low parameter actions
                    
                    # Provide action plans for high parameters, including dosing calculations for ammonia/nitrite.
                    for high_item in warning['high_warnings']:
                        param, value = high_item['param'], high_item['value']
                        plan_list = ACTION_PLANS.get(param, []).copy()
                        if volume_l and volume_l > 0 and param in ['ammonia', 'nitrite']:
                            # Suggest FritzZyme 7 for ammonia/nitrite issues.
                            dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system=True)
                            plan_list.insert(1, f"**Dosage:** For your {volume_l:.0f}L tank, dose **{dose_ml:.0f}ml / {dose_oz:.1f}oz** of FritzZyme 7.")
                        for step in plan_list:
                            st.markdown(f" • {step}")
                        st.markdown("---") # Separator between high parameter actions