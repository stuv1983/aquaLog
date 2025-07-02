# tabs/tools_tab.py

"""
tools_tab.py – Aquarium Calculators

Renders the "Tools" tab, which provides a collection of useful calculators.
This includes an Aquarium Volume Calculator based on tank dimensions and
a Dosing Calculator for common aquarium supplements, helping users with
precise measurements and chemical adjustments.
"""

from __future__ import annotations # Added for type hinting consistency

import streamlit as st
from typing import List, Optional, Any, Dict, Tuple # Ensure all necessary types are imported

from utils.chemistry import (
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
    calculate_fritzzyme7_dose,
    calculate_volume,
    calculate_water_change_percentage,
)
from aqualog_db.repositories import TankRepository
from aqualog_db.repositories.tank import TankRecord # Import TankRecord TypedDict

from utils import show_toast, request_rerun # Utilities for UI feedback

def render_volume_calculator() -> None: # Added return type hint
    """
    Renders the user interface for the Aquarium Volume Calculator.

    This calculator allows users to input tank dimensions (length, width, height)
    in either centimeters or inches, and it calculates the volume in liters and
    US gallons. It also provides an option to save the calculated volume to
    the currently selected tank in the database.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    # The form now only contains the input widgets and the primary calculation button.
    with st.form("volume_calculator_form"):
        st.subheader("📏 Aquarium Volume Calculator")
        st.write("Calculate the volume of your tank based on its dimensions.")
        
        # Radio buttons for selecting units (cm or inches)
        units: str = st.radio("Units", ["cm", "inches"], horizontal=True) # Explicitly type units
        
        # Input fields for length, width, and height, laid out in three columns
        col1, col2, col3 = st.columns(3)
        length: float = col1.number_input(f"Length ({units})", min_value=0.1, value=60.0, step=0.1) # Explicitly type length
        width: float = col2.number_input(f"Width ({units})", min_value=0.1, value=30.0, step=0.1) # Explicitly type width
        height: float = col3.number_input(f"Height ({units})", min_value=0.1, value=30.0, step=0.1) # Explicitly type height
        
        # Button to trigger the volume calculation
        submitted: bool = st.form_submit_button("Calculate Volume") # Explicitly type submitted
        
    # The results and the secondary "Save" button are now outside the form.
    if submitted:
        # Perform volume calculation using the chemistry utility function
        liters, gallons = calculate_volume(length, width, height, units)
        st.metric("Calculated Volume", f"{liters:.2f} Liters / {gallons:.2f} Gallons")
        
        # Get the currently selected tank ID from session state
        tank_id: Optional[int] = st.session_state.get("tank_id") # Explicitly type tank_id
        if tank_id:
            # This button is now outside the form and will work correctly.
            if st.button("Save this volume to current tank"):
                repo = TankRepository()
                repo.update_volume(tank_id, liters) # Update tank volume in the database
                show_toast("✅ Success", "Tank volume has been updated.") # Show success toast
                request_rerun() # Rerun to reflect changes


def render_dosing_calculator() -> None: # Added return type hint
    """
    Renders the user interface for the Dosing Calculator.

    This calculator helps users determine the appropriate dosage for various
    aquarium supplements (e.g., Seachem Alkaline Buffer, Seachem Equilibrium,
    FritzZyme 7) based on tank volume and desired parameter changes.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.subheader("🧪 Dosing Calculator")
    st.write("Select a product to calculate the required dosage for your tank.")

    # --- Get the current tank's volume ---
    # Attempt to pre-fill the volume input with the selected tank's volume.
    tank_id: Optional[int] = st.session_state.get("tank_id")
    tank_volume: float = 0.0
    if tank_id:
        repo = TankRepository()
        tanks: List[TankRecord] = repo.fetch_all() # Explicitly type tanks
        tank_info: Optional[TankRecord] = next((t for t in tanks if t['id'] == tank_id), None) # Explicitly type tank_info
        if tank_info and tank_info.get("volume_l"):
            tank_volume = float(tank_info["volume_l"]) # Ensure float for operations

    # Dropdown to select the product for which dosage needs to be calculated.
    product_options: Dict[str, str] = { # Explicitly type product_options
        "Seachem Alkaline Buffer (for KH)": "alkaline_buffer",
        "Seachem Equilibrium (for GH)": "equilibrium",
        "FritzZyme 7 (Nitrifying Bacteria)": "fritzzyme7",
    }
    
    selected_product_name: str = st.selectbox( # Explicitly type selected_product_name
        "Select Product", options=list(product_options.keys())
    )
    product_key: str = product_options[selected_product_name] # Explicitly type product_key
    
    st.markdown("---") # Separator

    # Form for product-specific inputs and dosage calculation.
    with st.form(key=f"{product_key}_form"):
        st.subheader(f"Inputs for: {selected_product_name}")
        # Input for tank volume, pre-filled with selected tank's volume if available.
        volume_l: float = st.number_input("Tank Volume (Liters)", min_value=0.1, value=tank_volume if tank_volume > 0 else 50.0) # Explicitly type volume_l

        # Conditional inputs based on the selected product.
        if product_key == "alkaline_buffer":
            current_kh: float = st.number_input("Current KH (dKH)", min_value=0.0, value=2.0, step=0.1) # Explicitly type current_kh
            target_kh: float = st.number_input("Target KH (dKH)", min_value=0.0, value=4.0, step=0.1) # Explicitly type target_kh
            delta_kh: float = target_kh - current_kh # Calculate difference for dosage # Explicitly type delta_kh
        elif product_key == "equilibrium":
            current_gh: float = st.number_input("Current GH (°dGH)", min_value=0.0, value=4.0, step=0.1) # Explicitly type current_gh
            target_gh: float = st.number_input("Target GH (°dGH)", min_value=0.0, value=6.0, step=0.1) # Explicitly type target_gh
            delta_gh: float = target_gh - current_gh # Calculate difference for dosage # Explicitly type delta_gh
        elif product_key == "fritzzyme7":
            is_new_system: bool = st.radio("System Type", ["New System", "Established System"]) == "New System" # Explicitly type is_new_system

        submitted: bool = st.form_submit_button("Calculate Dosage") # Explicitly type submitted
        
        # Display results upon form submission.
        if submitted:
            st.markdown("---")
            st.subheader("Results")
            if product_key == "alkaline_buffer":
                if delta_kh <= 0: st.success("KH is at or above target.")
                else: st.metric(f"Alkaline Buffer Needed", f"{calculate_alkaline_buffer_dose(volume_l, delta_kh):.2f} grams")
            elif product_key == "equilibrium":
                if delta_gh <= 0: st.success("GH is at or above target.")
                else: st.metric(f"Equilibrium Needed", f"{calculate_equilibrium_dose(volume_l, delta_gh):.2f} grams")
            elif product_key == "fritzzyme7":
                dose_ml, dose_oz = calculate_fritzzyme7_dose(volume_l, is_new_system)
                st.metric("Recommended FritzZyme 7 Dose", f"{dose_ml:.0f} ml  /  {dose_oz:.1f} oz")

def render_water_change_calculator() -> None: # Added return type hint
    """
    Renders the user interface for the Water Change Calculator.

    This calculator helps users determine the percentage of water to change
    to reduce a specific water parameter to a desired target level.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.subheader("💧 Water Change Calculator")
    st.write("Calculate the percentage of water to change to reduce a parameter.")

    # --- Get the current tank's volume ---
    tank_id: Optional[int] = st.session_state.get("tank_id") # Explicitly type tank_id
    tank_volume: float = 0.0
    if tank_id:
        repo = TankRepository()
        tanks: List[TankRecord] = repo.fetch_all() # Explicitly type tanks
        tank_info: Optional[TankRecord] = next((t for t in tanks if t['id'] == tank_id), None) # Explicitly type tank_info
        if tank_info and tank_info.get("volume_l"):
            tank_volume = float(tank_info["volume_l"]) # Ensure float for operations
    
    with st.form("water_change_form"):
        # Input for current parameter value
        current_value: float = st.number_input("Current Parameter Value", min_value=0.01, value=40.0, step=0.1, help="e.g., current Nitrate level") # Explicitly type current_value
        # Input for target parameter value
        target_value: float = st.number_input("Target Parameter Value", min_value=0.0, value=20.0, step=0.1, help="e.g., desired Nitrate level after water change") # Explicitly type target_value
        
        # Display current tank volume, or allow manual input if not available
        volume_l: float = st.number_input("Tank Volume (Liters)", min_value=0.1, value=tank_volume if tank_volume > 0 else 50.0) # Explicitly type volume_l

        submitted: bool = st.form_submit_button("Calculate Water Change") # Explicitly type submitted

    if submitted:
        if current_value <= 0:
            st.error("Current parameter value must be greater than 0.")
        elif target_value >= current_value:
            st.warning("Target value must be less than current value to calculate a reduction.")
        else:
            percentage: float = calculate_water_change_percentage(current_value, target_value) # Explicitly type percentage
            st.metric("Recommended Water Change", f"{percentage:.1f}%")
            
            # Calculate and display the actual volume to change
            volume_to_change: float = volume_l * (percentage / 100) # Explicitly type volume_to_change
            st.info(f"This equates to changing approximately **{volume_to_change:.1f} Liters** of water.")


def render_co2_canister_duration_calculator() -> None: # Added return type hint
    """
    Renders the user interface for the CO2 Canister Duration Calculator.

    This calculator estimates how long a CO2 canister will last based on
    its weight, bubbles per second, and hours the CO2 is active per day.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.subheader("💨 CO₂ Canister Duration Calculator")
    st.write("Estimate how long your CO₂ canister will last.")

    with st.form("co2_duration_form"):
        canister_weight_kg: float = st.number_input( # Explicitly type canister_weight_kg
            "CO₂ Canister Weight (kg)",
            min_value=0.1,
            value=1.0,
            step=0.1,
            help="Common sizes are 0.5kg, 1kg, 2kg, etc."
        )
        bps: float = st.number_input( # Explicitly type bps
            "Bubbles Per Second (BPS)",
            min_value=0.1,
            value=1.0,
            step=0.1,
            format="%.1f",
            help="Adjust this based on your bubble counter."
        )
        hours_on_per_day: int = st.number_input( # Explicitly type hours_on_per_day
            "Hours CO₂ is On Per Day",
            min_value=1,
            max_value=24,
            value=8,
            step=1,
            help="Typically synced with your light cycle."
        )

        submitted: bool = st.form_submit_button("Calculate Duration") # Explicitly type submitted

    if submitted:
        # Assumptions:
        # 1 kg liquid CO2 ~ 509 Liters of CO2 gas at STP (Standard Temperature and Pressure)
        # 1 bubble ~ 0.3 mL of CO2 gas (this is an approximation, can vary)
        
        # Convert canister weight to total mL of CO2 gas
        total_co2_gas_ml: float = canister_weight_kg * 509000 # Explicitly type total_co2_gas_ml

        # Calculate CO2 consumed per day in mL
        seconds_on_per_day: int = hours_on_per_day * 3600 # Explicitly type seconds_on_per_day
        co2_consumed_per_day_ml: float = bps * 0.3 * seconds_on_per_day # Explicitly type co2_consumed_per_day_ml

        if co2_consumed_per_day_ml <= 0:
            st.error("CO₂ consumption per day must be greater than zero. Please check your BPS and hours settings.")
            return

        # Calculate duration in days
        duration_days: float = total_co2_gas_ml / co2_consumed_per_day_ml # Explicitly type duration_days

        st.markdown("---")
        st.subheader("Estimated Duration")
        st.info(
            "**Note:** This is an approximation. Actual duration may vary based on temperature, pressure, "
            "equipment efficiency, and precise bubble size."
        )
        st.metric("Canister Will Last Approximately", f"{duration_days:.1f} Days")
        
        if duration_days < 30:
            st.warning("Your canister may not last very long. Consider a larger canister or reducing CO₂ usage.")
        elif duration_days < 90:
            st.info("Your canister should last a reasonable amount of time.")
        else:
            st.success("Your canister should last a long time!")


def tools_tab() -> None: # Added return type hint
    """
    Main function to render the "Aquarium Tools & Calculators" tab.

    This function serves as the entry point for the tools tab, allowing users
    to select and utilize either the Aquarium Volume Calculator or the Dosing Calculator.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    st.header("🛠️ Aquarium Tools & Calculators")
    
    # Check if any tank has CO2 enabled
    tank_repo = TankRepository()
    tanks = tank_repo.fetch_all()
    any_tank_has_co2 = any(tank.get("has_co2", True) for tank in tanks)

    # Selectbox to choose between different tools.
    tool_options = ["Aquarium Volume Calculator", "Dosing Calculator", "Water Change Calculator"]
    if any_tank_has_co2:
        tool_options.append("CO₂ Canister Duration Calculator")

    tool_choice: str = st.selectbox( # Explicitly type tool_choice
        "Select a Tool",
        tool_options
    )
    
    st.markdown("---") # Separator
    
    # Render the selected tool's UI.
    if tool_choice == "Aquarium Volume Calculator":
        render_volume_calculator()
    elif tool_choice == "Dosing Calculator":
        render_dosing_calculator()
    elif tool_choice == "Water Change Calculator":
        render_water_change_calculator()
    elif tool_choice == "CO₂ Canister Duration Calculator":
        render_co2_canister_duration_calculator()