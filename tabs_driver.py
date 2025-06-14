"""
tabs_driver.py – Main Tabs Driver (v3.3.0)
Renders the sidebar and all primary application tabs in the correct order.
Updated: 2025-06-09
"""
import streamlit as st

from tabs.sidebar_entry        import sidebar_entry
from tabs.overview_tab         import overview_tab
from tabs.warnings_tab         import warnings_tab
from tabs.data_analytics_tab   import data_analytics_tab
from tabs.cycle_tab            import cycle_tab
from tabs.failed_tests_tab     import failed_tests_tab
from tabs.plant_inventory_tab  import plant_inventory_tab
from tabs.fish_inventory_tab   import fish_inventory_tab
from tabs.equipment_tab        import equipment_tab     # <-- new
from tabs.maintenance_tab      import maintenance_tab

def main():
    """
    Entry point for the AquaLog Streamlit app. Renders the sidebar and main tabs.
    """
    # 1) Render sidebar (Log Water Test form, release notes, etc.)
    sidebar_entry()

    # 2) Define tab titles and their corresponding render functions, in order:
    tab_titles = [
        "Overview",          # 0
        "Warnings",          # 1
        "Data & Analytics",  # 2
        "Cycle",             # 3  
        "Failed Tests",      # 4
        "Plants",            # 5
        "Fish",              # 6
        "Equipment",         # 7  
        "Maintenance",       # 8
    ]

    tab_funcs = [
        overview_tab,
        warnings_tab,
        data_analytics_tab,
        cycle_tab,           
        failed_tests_tab,
        plant_inventory_tab,
        fish_inventory_tab,
        equipment_tab,      
        maintenance_tab,
    ]

    # 3) Create Streamlit tabs using the defined titles
    tabs = st.tabs(tab_titles)

    # 4) For each tab, call its render function inside the with-block
    for tab_obj, func in zip(tabs, tab_funcs):
        with tab_obj:
            func()


if __name__ == "__main__":
    main()
