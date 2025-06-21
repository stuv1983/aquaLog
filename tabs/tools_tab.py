# tabs/tools_tab.py

"""
tools_tab.py – Aquarium Calculators

Renders the "Tools" tab, which provides a collection of useful calculators.
This includes an Aquarium Volume Calculator based on tank dimensions and
a Dosing Calculator for common aquarium supplements, helping users with
precise measurements and chemical adjustments.
"""

import streamlit as st

from utils.chemistry import (
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
    calculate_fritzzyme7_dose,
    calculate_volume, # Import the new volume calculator
    calculate_water_change_percentage, # Import the new water change percentage calculator
)
from aqualog_db.repositories import TankRepository
from utils import show_toast, request_rerun # Utilities for UI feedback

def render_volume_calculator():
    """
    Renders the user interface for the Aquarium Volume Calculator.

    This calculator allows users to input tank dimensions (length, width, height)
    in either centimeters or inches, and it calculates the volume in liters and
    US gallons. It also provides an option to save the calculated volume to
    the currently selected tank in the database.
    """
    # The form now only contains the input widgets and the primary calculation button.
    with st.form("volume_calculator_form"):
        st.subheader("📏 Aquarium Volume Calculator")
        st.write("Calculate the volume of your tank based on its dimensions.")
        
        # Radio buttons for selecting units (cm or inches)
        units = st.radio("Units", ["cm", "inches"], horizontal=True)
        
        # Input fields for length, width, and height, laid out in three columns
        col1, col2, col3 = st.columns(3)
        length = col1.number_input(f"Length ({units})", min_value=0.1, value=60.0, step=0.1)
        width = col2.number_input(f"Width ({units})", min_value=0.1, value=30.0, step=0.1)
        height = col3.number_input(f"Height ({units})", min_value=0.1, value=30.0, step=0.1)
        
        # Button to trigger the volume calculation
        submitted = st.form_submit_button("Calculate Volume")
        
    # The results and the secondary "Save" button are now outside the form.
    if submitted:
        # Perform volume calculation using the chemistry utility function
        liters, gallons = calculate_volume(length, width, height, units)
        st.metric("Calculated Volume", f"{liters:.2f} Liters / {gallons:.2f} Gallons")
        
        # Get the currently selected tank ID from session state
        tank_id = st.session_state.get("tank_id")
        if tank_id:
            # This button is now outside the form and will work correctly.
            if st.button("Save this volume to current tank"):
                repo = TankRepository()
                repo.update_volume(tank_id, liters) # Update tank volume in the database
                show_toast("✅ Success", "Tank volume has been updated.") # Show success toast
                request_rerun() # Rerun to reflect changes


def render_dosing_calculator():
    """
    Renders the user interface for the Dosing Calculator.

    This calculator helps users determine the appropriate dosage for various
    aquarium supplements (e.g., Seachem Alkaline Buffer, Seachem Equilibrium,
    FritzZyme 7) based on tank volume and desired parameter changes.
    """
    st.subheader("🧪 Dosing Calculator")
    st.write("Select a product to calculate the required dosage for your tank.")

    # --- Get the current tank's volume ---
    # Attempt to pre-fill the volume input with the selected tank's volume.
    tank_id = st.session_state.get("tank_id")
    tank_volume = 0.0
    if tank_id:
        repo = TankRepository()
        # Fetch all tanks and find the current one's volume.
        # A more direct `repo.get_by_id(tank_id)` would be slightly more efficient.
        tanks = repo.fetch_all()
        tank_info = next((t for t in tanks if t['id'] == tank_id), None)
        if tank_info and tank_info.get("volume_l"):
            tank_volume = tank_info["volume_l"]

    # Dropdown to select the product for which dosage needs to be calculated.
    product_options = {
        "Seachem Alkaline Buffer (for KH)": "alkaline_buffer",
        "Seachem Equilibrium (for GH)": "equilibrium",
        "FritzZyme 7 (Nitrifying Bacteria)": "fritzzyme7",
    }
    
    selected_product_name = st.selectbox(
        "Select Product", options=list(product_options.keys())
    )
    product_key = product_options[selected_product_name]
    
    st.markdown("---") # Separator

    # Form for product-specific inputs and dosage calculation.
    with st.form(key=f"{product_key}_form"):
        st.subheader(f"Inputs for: {selected_product_name}")
        # Input for tank volume, pre-filled with selected tank's volume if available.
        volume_l = st.number_input("Tank Volume (Liters)", min_value=0.1, value=tank_volume if tank_volume > 0 else 50.0)

        # Conditional inputs based on the selected product.
        if product_key == "alkaline_buffer":
            current_kh = st.number_input("Current KH (dKH)", min_value=0.0, value=2.0, step=0.1)
            target_kh = st.number_input("Target KH (dKH)", min_value=0.0, value=4.0, step=0.1)
            delta_kh = target_kh - current_kh # Calculate difference for dosage
        elif product_key == "equilibrium":
            current_gh = st.number_input("Current GH (°dGH)", min_value=0.0, value=4.0, step=0.1)
            target_gh = st.number_input("Target GH (°dGH)", min_value=0.0, value=6.0, step=0.1)
            delta_gh = target_gh - current_gh # Calculate difference for dosage
        elif product_key == "fritzzyme7":
            is_new_system = st.radio("System Type", ["New System", "Established System"]) == "New System"

        submitted = st.form_submit_button("Calculate Dosage")
        
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

def render_water_change_calculator():
    """
    Renders the user interface for the Water Change Calculator.

    This calculator helps users determine the percentage of water to change
    to reduce a specific water parameter to a desired target level.
    """
    st.subheader("💧 Water Change Calculator")
    st.write("Calculate the percentage of water to change to reduce a parameter.")

    # --- Get the current tank's volume ---
    tank_id = st.session_state.get("tank_id")
    tank_volume = 0.0
    if tank_id:
        repo = TankRepository()
        tanks = repo.fetch_all()
        tank_info = next((t for t in tanks if t['id'] == tank_id), None)
        if tank_info and tank_info.get("volume_l"):
            tank_volume = tank_info["volume_l"]
    
    with st.form("water_change_form"):
        # Input for current parameter value
        current_value = st.number_input("Current Parameter Value", min_value=0.01, value=40.0, step=0.1, help="e.g., current Nitrate level")
        # Input for target parameter value
        target_value = st.number_input("Target Parameter Value", min_value=0.0, value=20.0, step=0.1, help="e.g., desired Nitrate level after water change")
        
        # Display current tank volume, or allow manual input if not available
        volume_l = st.number_input("Tank Volume (Liters)", min_value=0.1, value=tank_volume if tank_volume > 0 else 50.0)

        submitted = st.form_submit_button("Calculate Water Change")

    if submitted:
        if current_value <= 0:
            st.error("Current parameter value must be greater than 0.")
        elif target_value >= current_value:
            st.warning("Target value must be less than current value to calculate a reduction.")
        else:
            percentage = calculate_water_change_percentage(current_value, target_value)
            st.metric("Recommended Water Change", f"{percentage:.1f}%")
            
            # Calculate and display the actual volume to change
            volume_to_change = volume_l * (percentage / 100)
            st.info(f"This equates to changing approximately **{volume_to_change:.1f} Liters** of water.")


def tools_tab():
    """
    Main function to render the "Aquarium Tools & Calculators" tab.

    This function serves as the entry point for the tools tab, allowing users
    to select and utilize either the Aquarium Volume Calculator or the Dosing Calculator.
    """
    st.header("🛠️ Aquarium Tools & Calculators")
    
    # Selectbox to choose between different tools.
    tool_choice = st.selectbox(
        "Select a Tool",
        ("Aquarium Volume Calculator", "Dosing Calculator", "Water Change Calculator")
    )
    
    st.markdown("---") # Separator
    
    # Render the selected tool's UI.
    if tool_choice == "Aquarium Volume Calculator":
        render_volume_calculator()
    elif tool_choice == "Dosing Calculator":
        render_dosing_calculator()
    elif tool_choice == "Water Change Calculator":
        render_water_change_calculator()