# config.py

"""
config.py – Central Configuration File

Defines global constants and settings used throughout the application. This
includes safe ranges for water parameters, action plans for warnings, unit
conversion factors, and localization strings.
"""

import os
from typing import Callable, Any

# Path to the SQLite database file. It will be created in the current working directory.
DB_FILE: str = os.path.join(os.getcwd(), "aqualog.db")

# Dictionary defining the ideal/safe ranges for various water parameters.
# Format: "parameter_name": (safe_low_value, safe_high_value)
SAFE_RANGES: dict[str, tuple[float, float]] = {
    "temperature":   (18.0, 28.0), # Temperature in Celsius
    "ammonia":       (0.0, 0.0),   # Ammonia in parts per million (ppm) - ideally 0
    "nitrite":       (0.0, 0.0),   # Nitrite in ppm - ideally 0
    "nitrate":       (20.0, 50.0), # Nitrate in ppm (target for planted tanks)
    "ph":            (6.0, 8.0),   # pH value (unitless)
    "kh":            (4.0, 8.0),   # Carbonate Hardness in dKH (degrees of Carbonate Hardness)
    "gh":            (6.0, 10.0),  # General Hardness in dGH (degrees of General Hardness)
    "co2_indicator": (2.0, 2.0), # CO2 indicator value (conceptual for 'Green' state)
}

# Thresholds below which a parameter is considered "too low".
# Format: "parameter_name": threshold_value
TOO_LOW_THRESHOLDS: dict[str, float] = {
    "nitrate":       20.0,
    "kh":            4.0,
    "ph":            6.0,
    "co2_indicator": 2.0, # Corresponds to "Blue" indicator
}

# Thresholds above which a parameter is considered "too high".
# Format: "parameter_name": threshold_value
TOO_HIGH_THRESHOLDS: dict[str, float] = {
    "temperature":   28.0,
    "nitrite":       0.0, # Any non-zero nitrite is too high
    "nitrate":       50.0,
    "ph":            8.0,
    "kh":            8.0,
    "gh":            10.0,
    "co2_indicator": 2.0, # Corresponds to "Yellow" indicator
    "ammonia":       0.02, # Any non-zero unionized ammonia is too high (specific for calculation)
}

# Action plans provided when a parameter is detected as "too low".
# Format: "parameter_name": [list_of_action_steps_as_strings]
LOW_ACTION_PLANS: dict[str, list[str]] = {
    "nitrate": [
        "Nitrate is low (<20 ppm). Dose a nitrate fertilizer to reach the 20-40 ppm target range.",
        "If plants show deficiencies despite dosing, consider minor changes to feeding or livestock.",
    ],
    "co2_indicator": [
        "CO₂ is low. Gradually increase the injection rate and ensure good circulation to improve mixing.",
    ],
    "kh": [
        "KH is critically low (<4 dKH), which can lead to unstable pH. Dose an alkaline buffer to raise KH towards the 4-6 dKH range.",
        "Test KH daily after adjustments until it remains stable.",
    ],
    "ph": [
        "pH is very low (<6.0). Use a neutral regulator or other buffer to gradually raise the pH, avoiding sudden changes that can shock livestock.",
    ],
    "gh": [
        "GH is low (<6 dGH). Add a remineralizer (e.g., Seachem Equilibrium) to reach the 6-8 dGH target range.",
        "Test GH weekly after adjustments until stable.",
    ],
}

# Action plans provided when a parameter is detected as "too high".
# Format: "parameter_name": [list_of_action_steps_as_strings]
ACTION_PLANS: dict[str, list[str]] = {
    "temperature": [
        "Temperature is high (>28°C). Turn off the aquarium heater and increase surface agitation for better oxygen exchange.",
        "If ambient room temperature is high, use a cooling fan or float sealed bottles of ice to gently lower the temperature.",
    ],
    "ammonia": [
        "Ammonia is present. Perform an immediate 50% water change to reduce toxicity.",
        "Dose with FritzZyme 7 Live Nitrifying Bacteria: Use 4oz (119ml) per 10 US Gallons for new tanks, or 2oz (60ml) for established tanks.",
        "Consider using a detoxifier like Seachem Prime for immediate fish protection.",
        "Stop feeding for 24-48 hours and ensure the tank is well-aerated."
    ],
    "nitrite": [
        "Nitrite is present (>0 ppm), which is highly toxic to fish. Perform a 30-50% water change.",
        "Dose with FritzZyme 7 Live Nitrifying Bacteria to accelerate processing: Use 4oz (119ml) per 10 US Gallons for new tanks, or 2oz (60ml) for established tanks.",
        "Ensure high aeration to maximize oxygen levels and support the bacteria."
    ],
    "nitrate": [
        "Nitrate is high (>50 ppm). Perform a 30-50% water change to lower levels.",
        "To manage nitrates long-term, reduce feeding, add fast-growing plants, and ensure regular substrate cleaning.",
    ],
    "ph": [
        "pH is high (>8.0). Perform partial water changes using softer water (like RO or rainwater) to lower it.",
        "Investigate and remove any alkaline-leaching decor, such as certain rocks or substrate.",
    ],
    "kh": [
        "KH is high (>8 dKH), which can make pH difficult to lower. Pause the use of all buffering additives.",
        "Use reverse osmosis (RO) or rainwater for top-offs and water changes to gradually reduce KH.",
    ],
    "gh": [
        "GH is high (>10 dGH). Stop dosing any remineralizing additives.",
        "Perform partial water changes with reverse osmosis (RO) or other soft water to dilute the mineral content.",
    ],
    "co2_indicator": [
        "CO₂ is too high. Reduce the CO₂ injection rate and, if necessary, increase surface agitation to off-gas excess CO₂.",
    ],
}

# Advice messages based on CO2 indicator color (e.g., from a drop checker).
# Format: "color_string": "advice_message"
CO2_COLOR_ADVICE: dict[str, str] = {
    "Blue":   "CO₂ low – raise injection rate.",
    "Green":  "CO₂ ideal – no action.",
    "Yellow": "CO₂ high – reduce injection / add aeration.",
}

# Localization strings for different locales.
# Format: "locale_code": {"original_label": "translated_label"}
LOCALIZATIONS: dict[str, dict[str, str]] = {
    "en_US": {
        "Temperature":      "Temperature",
        "pH":               "pH",
        "Ammonia":          "Ammonia",
        "Nitrite":          "Nitrite",
        "Nitrate":          "Nitrate",
        "KH":               "KH",
        "GH":               "GH",
        "Drop Checker":     "CO₂ Indicator",
        "is too low":       "is too low",
        "is too high":      "is too high",
        "Latest test":      "Latest test",
        "out-of-range":     "out-of-range",
        "Dismiss Warning":  "Dismiss Warning",
        "Show Warning":     "Show Warning",
    },
    # Future: Add other languages here, e.g., "es_ES": {...}
}

# Defines the display units for different parameters based on the selected unit system.
# Format: "System_Name": {"parameter_name": "unit_string"}
UNIT_SYSTEMS: dict[str, dict[str, str]] = {
    "Metric": {
        "temperature":   "°C",
        "ammonia":       "ppm",
        "nitrite":       "ppm",
        "nitrate":       "ppm",
        "ph":            "",     # pH is unitless
        "kh":            "°dKH",
        "gh":            "°dGH",
        "co2_indicator": "",     # CO2 indicator is unitless (color-based)
    },
    "Imperial": {
        "temperature":   "°F",
        "ammonia":       "ppm",
        "nitrite":       "ppm",
        "nitrate":       "ppm",
        "ph":            "",
        "kh":            "°dKH",  # General Hardness used for KH in some imperial contexts
        "gh":            "°GH",
        "co2_indicator": "",
    },
    # Future: Add other unit systems as needed
}

# Dictionary of conversion functions between different units.
# Keys are tuples (from_unit, to_unit), values are lambda functions for conversion.
CONVERSIONS: dict[tuple[str, str], Callable[[float], float]] = {
    ("°C", "°F"): lambda c: c * 9 / 5 + 32,
    ("°F", "°C"): lambda f: (f - 32) * 5 / 9,
}

def is_too_low(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is below its configured 'too low' threshold.

    Args:
        param: The name of the parameter (e.g., "nitrate", "kh").
        value: The measured value of the parameter.

    Returns:
        True if the value is below the threshold, False otherwise.
    """
    thresh = TOO_LOW_THRESHOLDS.get(param)
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    """
    Checks if a parameter's value is above its configured 'too high' threshold.

    Args:
        param: The name of the parameter (e.g., "temperature", "ammonia").
        value: The measured value of the parameter.

    Returns:
        True if the value is above the threshold, False otherwise.
    """
    thresh = TOO_HIGH_THRESHOLDS.get(param)
    return thresh is not None and value > thresh

def get_low_action_plan(param: str) -> list[str]:
    """
    Retrieves the action plan for a parameter when its value is too low.

    Args:
        param: The name of the parameter.

    Returns:
        A list of strings representing the action plan steps, or an empty list if no plan exists.
    """
    return list(LOW_ACTION_PLANS.get(param, []))

def get_high_action_plan(param: str) -> list[str]:
    """
    Retrieves the action plan for a parameter when its value is too high.

    Args:
        param: The name of the parameter.

    Returns:
        A list of strings representing the action plan steps, or an empty list if no plan exists.
    """
    return list(ACTION_PLANS.get(param, []))

# Configuration for the weekly summary email feature.
WEEKLY_EMAIL_TIME: dict[str, Any] = {
    'day_of_week': 'mon',         # Day of the week to send the email (e.g., 'mon', 'tue')
    'hour': 9,                    # Hour to send the email (24-hour format)
    'minute': 0,                  # Minute to send the email
    'from_address': 'your_email@example.com', # Sender's email address
    'smtp': {                     # SMTP server settings
        'host': 'smtp.example.com', # SMTP host
        'port': 587,                # SMTP port (e.g., 587 for TLS)
        'tls': True,                # Use TLS encryption
        'username': 'smtp_user',    # SMTP username
        'password': 'smtp_password',# SMTP password (consider environment variables for production)
    },
}

# Current version of the application.
VERSION = "v3.7.1"

# Release notes for the current version.
RELEASE_NOTES = """
### v3.7.1 (2025-06-12)
* **Fix:** Database now persists to `aqualog.db` on disk.
* **Fix:** `init_tables()` called at startup to initialize/migrate schema.
"""