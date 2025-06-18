# tabs/tools_tab.py

"""
tools_tab.py – Aquarium Calculators

Renders the "Tools" tab, which provides a collection of useful calculators.
This includes a Dosing Calculator for common supplements and an Aquarium Volume
Calculator based on tank dimensions.
"""

import streamlit as st

from utils.chemistry import (
    calculate_alkaline_buffer_dose,
    calculate_equilibrium_dose,
    calculate_fritzzyme7_dose,
    calculate_volume, # Import the new volume calculator
)
from aqualog_db.repositories import TankRepository
from utils import show_toast, request_rerun

def render_volume_calculator():
    """Renders the UI for the Aquarium Volume Calculator."""
    # The form now only contains the input widgets and the primary calculation button.
    with st.form("volume_calculator_form"):
        st.subheader("📏 Aquarium Volume Calculator")
        st.write("Calculate the volume of your tank based on its dimensions.")
        
        units = st.radio("Units", ["cm", "inches"], horizontal=True)
        
        col1, col2, col3 = st.columns(3)
        length = col1.number_input(f"Length ({units})", min_value=0.1, value=60.0, step=0.1)
        width = col2.number_input(f"Width ({units})", min_value=0.1, value=30.0, step=0.1)
        height = col3.number_input(f"Height ({units})", min_value=0.1, value=30.0, step=0.1)
        
        submitted = st.form_submit_button("Calculate Volume")
        
    # The results and the secondary "Save" button are now outside the form.
    if submitted:
        liters, gallons = calculate_volume(length, width, height, units)
        st.metric("Calculated Volume", f"{liters:.2f} Liters / {gallons:.2f} Gallons")
        
        tank_id = st.session_state.get("tank_id")
        if tank_id:
            # This button is now outside the form and will work correctly.
            if st.button("Save this volume to current tank"):
                repo = TankRepository()
                repo.update_volume(tank_id, liters)
                show_toast("✅ Success", "Tank volume has been updated.")
                request_rerun()


def render_dosing_calculator():
    """Renders the UI for the Dosing Calculator."""
    st.subheader("🧪 Dosing Calculator")
    st.write("Select a product to calculate the required dosage for your tank.")

    # --- Get the current tank's volume ---
    tank_id = st.session_state.get("tank_id")
    tank_volume = 0.0
    if tank_id:
        repo = TankRepository()
        # A new repo method to get a single tank would be better, but this works for now.
        tanks = repo.fetch_all()
        tank_info = next((t for t in tanks if t['id'] == tank_id), None)
        if tank_info and tank_info.get("volume_l"):
            tank_volume = tank_info["volume_l"]

    product_options = {
        "Seachem Alkaline Buffer (for KH)": "alkaline_buffer",
        "Seachem Equilibrium (for GH)": "equilibrium",
        "FritzZyme 7 (Nitrifying Bacteria)": "fritzzyme7",
    }
    
    selected_product_name = st.selectbox(
        "Select Product", options=list(product_options.keys())
    )
    product_key = product_options[selected_product_name]
    
    st.markdown("---")

    with st.form(key=f"{product_key}_form"):
        st.subheader(f"Inputs for: {selected_product_name}")
        volume_l = st.number_input("Tank Volume (Liters)", min_value=0.1, value=tank_volume if tank_volume > 0 else 50.0)

        if product_key == "alkaline_buffer":
            current_kh = st.number_input("Current KH (dKH)", min_value=0.0, value=2.0, step=0.1)
            target_kh = st.number_input("Target KH (dKH)", min_value=0.0, value=4.0, step=0.1)
            delta_kh = target_kh - current_kh
        elif product_key == "equilibrium":
            current_gh = st.number_input("Current GH (°dGH)", min_value=0.0, value=4.0, step=0.1)
            target_gh = st.number_input("Target GH (°dGH)", min_value=0.0, value=6.0, step=0.1)
            delta_gh = target_gh - current_gh
        elif product_key == "fritzzyme7":
            is_new_system = st.radio("System Type", ["New System", "Established System"]) == "New System"

        submitted = st.form_submit_button("Calculate Dosage")
        
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

def tools_tab():
    """Main function to render the Tools tab."""
    st.header("🛠️ Aquarium Tools & Calculators")
    
    tool_choice = st.selectbox(
        "Select a Tool",
        ("Aquarium Volume Calculator", "Dosing Calculator")
    )
    
    st.markdown("---")
    
    if tool_choice == "Aquarium Volume Calculator":
        render_volume_calculator()
    elif tool_choice == "Dosing Calculator":
        render_dosing_calculator()
