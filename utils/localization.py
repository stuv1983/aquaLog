from typing import Dict, Optional
import streamlit as st

from config import LOCALIZATIONS, UNIT_SYSTEMS, CONVERSIONS

def translate(label: str) -> str:
    """
    Translates a label to the current locale's language.
    
    Args:
        label: The text label to translate
        
    Returns:
        Translated text or original label if no translation found
    """
    loc = st.session_state.get("locale", "en_US")
    return LOCALIZATIONS.get(loc, {}).get(label, label)

def convert_value(value: float, param: str) -> float:
    """
    Converts a value between unit systems based on the current setting.
    
    Args:
        value: The value to convert
        param: The parameter being converted (e.g., 'temperature')
        
    Returns:
        Converted value or original if no conversion needed
    """
    system = st.session_state.get("units", "Metric")
    from_u = UNIT_SYSTEMS["Metric"].get(param)
    to_u = UNIT_SYSTEMS.get(system, {}).get(param)
    if from_u and to_u and (from_u, to_u) in CONVERSIONS:
        return CONVERSIONS[(from_u, to_u)](value)
    return value

def format_with_units(value: float, param: str) -> str:
    """
    Formats a value with its appropriate unit based on current settings.
    
    Args:
        value: The numeric value to format
        param: The parameter being formatted
        
    Returns:
        Formatted string with value and unit
    """
    v = convert_value(value, param)
    unit = UNIT_SYSTEMS[st.session_state.get("units", "Metric")].get(param, "")
    return f"{v:.1f} {unit}".strip()