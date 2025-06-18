# config.py

"""
config.py – Central Configuration File

Defines global constants and settings used throughout the application. This
includes safe ranges for water parameters, action plans for warnings, unit
conversion factors, and localization strings.
"""

import os
from typing import Callable, Any

DB_FILE: str = os.path.join(os.getcwd(), "aqualog.db")

SAFE_RANGES: dict[str, tuple[float, float]] = {
    "temperature":   (18.0, 28.0),
    "ammonia":       (0.0, 0.0),
    "nitrite":       (0.0, 0.0),
    "nitrate":       (20.0, 50.0),
    "ph":            (6.0, 8.0),
    "kh":            (4.0, 8.0),
    "gh":            (6.0, 10.0),
    "co2_indicator": (2.0, 2.0),
}

TOO_LOW_THRESHOLDS: dict[str, float] = {
    "nitrate":       20.0,
    "kh":            4.0,
    "ph":            6.0,
    "co2_indicator": 2.0,
}

TOO_HIGH_THRESHOLDS: dict[str, float] = {
    "temperature":   28.0,
    "nitrite":       0.0,
    "nitrate":       50.0,
    "ph":            8.0,
    "kh":            8.0,
    "gh":            10.0,
    "co2_indicator": 2.0,
    "ammonia":       0.02,
}

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

CO2_COLOR_ADVICE: dict[str, str] = {
    "Blue":   "CO₂ low – raise injection rate.",
    "Green":  "CO₂ ideal – no action.",
    "Yellow": "CO₂ high – reduce injection / add aeration.",
}

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
}

UNIT_SYSTEMS: dict[str, dict[str, str]] = {
    "Metric": {
        "temperature":   "°C",
        "ammonia":       "ppm",
        "nitrite":       "ppm",
        "nitrate":       "ppm",
        "ph":            "",
        "kh":            "°dKH",
        "gh":            "°dGH",
        "co2_indicator": "",
    },
    "Imperial": {
        "temperature":   "°F",
        "ammonia":       "ppm",
        "nitrite":       "ppm",
        "nitrate":       "ppm",
        "ph":            "",
        "kh":            "°GH",
        "gh":            "°GH",
        "co2_indicator": "",
    },
}

CONVERSIONS: dict[tuple[str, str], Callable[[float], float]] = {
    ("°C", "°F"): lambda c: c * 9 / 5 + 32,
    ("°F", "°C"): lambda f: (f - 32) * 5 / 9,
}

def is_too_low(param: str, value: float) -> bool:
    thresh = TOO_LOW_THRESHOLDS.get(param)
    return thresh is not None and value < thresh

def is_too_high(param: str, value: float) -> bool:
    thresh = TOO_HIGH_THRESHOLDS.get(param)
    return thresh is not None and value > thresh

def get_low_action_plan(param: str) -> list[str]:
    return list(LOW_ACTION_PLANS.get(param, []))

def get_high_action_plan(param: str) -> list[str]:
    return list(ACTION_PLANS.get(param, []))

WEEKLY_EMAIL_TIME: dict[str, Any] = {
    'day_of_week': 'mon',
    'hour': 9,
    'minute': 0,
    'from_address': 'your_email@example.com',
    'smtp': {
        'host': 'smtp.example.com',
        'port': 587,
        'tls': True,
        'username': 'smtp_user',
        'password': 'smtp_password',
    },
}

VERSION = "v3.7.1"
RELEASE_NOTES = """
### v3.7.1 (2025-06-12)
* **Fix:** Database now persists to `aqualog.db` on disk.
* **Fix:** `init_tables()` called at startup to initialize/migrate schema.
"""