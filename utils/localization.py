# utils/localization.py

"""
localization.py – Translation and Unit Conversion

Handles localization and unit conversion for the application. It allows for
switching between languages and converting between different measurement
systems (e.g., Metric/Imperial), ensuring that numerical values are
displayed with appropriate units and translations.
"""

from typing import Dict, Optional
import streamlit as st

from config import LOCALIZATIONS, UNIT_SYSTEMS, CONVERSIONS

def translate(label: str) -> str:
    """
    Translates a given text label to the language of the current locale.

    The current locale is determined from Streamlit's session state. If no
    translation is found for the given label in the selected locale,
    the original label is returned.

    Args:
        label: The text label to translate.

    Returns:
        str: The translated text or the original label if no translation is found.
    """
    # Get the current locale from Streamlit's session state, defaulting to 'en_US'.
    loc = st.session_state.get("locale", "en_US")
    # Look up the translation in the LOCALIZATIONS dictionary.
    # .get(loc, {}) provides a safe fallback to an empty dict if locale is not found.
    # .get(label, label) provides the original label as a fallback if translation is missing.
    return LOCALIZATIONS.get(loc, {}).get(label, label)

def convert_value(value: float, param: str) -> float:
    """
    Converts a numeric value for a given parameter between different unit systems
    based on the current unit setting in Streamlit's session state.

    It uses predefined conversion functions from the `CONVERSIONS` dictionary.

    Args:
        value: The numeric value to convert.
        param: The name of the parameter (e.g., 'temperature', 'kh') whose
               value needs conversion.

    Returns:
        float: The converted value. Returns the original value if no conversion
               is needed or no appropriate conversion function is found.
    """
    # Get the target unit system from Streamlit's session state, defaulting to 'Metric'.
    system = st.session_state.get("units", "Metric")
    
    # Determine the "from" unit (always assumed to be Metric's unit for this param)
    from_u = UNIT_SYSTEMS["Metric"].get(param)
    # Determine the "to" unit based on the selected system.
    to_u = UNIT_SYSTEMS.get(system, {}).get(param)
    
    # Check if a conversion is defined between the determined units.
    if from_u and to_u and (from_u, to_u) in CONVERSIONS:
        # If a conversion function exists, apply it.
        return CONVERSIONS[(from_u, to_u)](value)
    
    # If no conversion is needed or found, return the original value.
    return value

def format_with_units(value: float, param: str) -> str:
    """
    Formats a numeric value by first converting it to the currently selected
    unit system and then appending its appropriate unit.

    Args:
        value: The numeric value to format.
        param: The name of the parameter.

    Returns:
        str: The formatted string with the value and its unit (e.g., "25.0 °C", "7.2").
    """
    # Convert the value to the current unit system.
    v = convert_value(value, param)
    
    # Get the unit symbol for the current parameter and unit system.
    unit = UNIT_SYSTEMS[st.session_state.get("units", "Metric")].get(param, "")
    
    # Format the value to one decimal place and append the unit.
    # .strip() is used to remove leading/trailing whitespace if the unit is empty.
    return f"{v:.1f} {unit}".strip()