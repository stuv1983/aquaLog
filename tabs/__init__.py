# tabs/__init__.py

"""
Initializes the 'tabs' module as a Python package and exposes all tab
rendering functions for direct import.
"""

from .cycle_tab import cycle_tab
from .data_analytics_tab import data_analytics_tab
from .equipment_tab import equipment_tab
from .failed_tests_tab import failed_tests_tab
from .fish_inventory_tab import fish_inventory_tab
from .maintenance_tab import maintenance_tab
from .overview_tab import overview_tab
from .plant_inventory_tab import plant_inventory_tab
from .tools_tab import tools_tab
from .warnings_tab import warnings_tab

__all__ = [
    "cycle_tab",
    "data_analytics_tab",
    "equipment_tab",
    "failed_tests_tab",
    "fish_inventory_tab",
    "maintenance_tab",
    "overview_tab",
    "plant_inventory_tab",
    "tools_tab",
    "warnings_tab",
]