# config.py

"""
config.py – Central configuration for AquaLog

Defines global constants used for parameter thresholds, action plans,
and the on-disk SQLite database path.
"""

import os
from typing import Callable, Any

# ──────────────────────────────────────────────────────────────
# Database path (persistent on-disk file)
# ──────────────────────────────────────────────────────────────
# This is the single source of truth for where the SQLite DB lives.
DB_FILE: str = os.path.join(os.getcwd(), "aqualog.db")

# ──────────────────────────────────────────────────────────────
# Safe operating windows (inclusive)
# ──────────────────────────────────────────────────────────────
SAFE_RANGES: dict[str, tuple[float, float]] = {
    "temperature":   (18.0, 28.0),   # °C
    "ammonia":       (0.0, 0.0),     # total ammonia; unionised NH₃ toxicity separate
    "nitrite":       (0.0, 0.0),     # ppm
    "nitrate":       (20.0, 50.0),   # ppm
    "ph":            (6.0, 8.0),     # pH units
    "kh":            (4.0, 8.0),     # °dKH
    "gh":            (6.0, 10.0),    # °dGH
    "co2_indicator": (2.0, 2.0),     # Drop-checker colour (Green)
}

# ──────────────────────────────────────────────────────────────
# One-sided danger thresholds
# ──────────────────────────────────────────────────────────────
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
    "ammonia":       0.02,  # NH₃ toxicity threshold
}

# ──────────────────────────────────────────────────────────────
# Action plans – guidance when parameters are outside safe windows
# ──────────────────────────────────────────────────────────────
LOW_ACTION_PLANS: dict[str, list[str]] = {
    "nitrate": [
        "⚠️ Nitrate is low (below 20 ppm).",
        "Dose a nitrate fertiliser until you reach 20–40 ppm.",
        "Consider heavier feeding or more livestock only if plants still starve.",
    ],
    "co2_indicator": [
        "CO₂ is low – raise injection rate and improve mixing.",
    ],
    "kh": [
        "KH is low (<4 dKH). Dose an alkaline buffer to bring KH to 6 dKH.",
        "Re-test KH daily until stable.",
    ],
    "ph": [
        "pH is low (<6.0). Dose Neutral Regulator gradually; avoid sudden shifts.",
    ],
    "gh": [
        "GH is low (<6.0 dGH). Add remineralizer (e.g. Seachem Equilibrium).",
        "Target GH of 6–8 dGH; re-test weekly.",
    ],
}

ACTION_PLANS: dict[str, list[str]] = {
    "temperature": [
        "Temperature high (>28 °C): turn off heater and increase surface agitation.",
        "Use a fan or floating ice bottles if ambient temps stay high.",
    ],
    "ammonia": [
        "Ammonia detected – perform a 50% water change immediately.",
        "Seed with nitrifying culture (e.g. FritzZyme TurboStart, Tetra SafeStart+).",
        "Stop feeding and maximise aeration.",
    ],
    "nitrite": [
        "Nitrite detected (>0.0 ppm) – perform a 30–50% water change.",
        "Seed with nitrifying bacteria and run air stones 24/7.",
    ],
    "nitrate": [
        "⚠️ Nitrate is high (>50 ppm). Perform a 30–50% water change.",
        "Reduce feeding and add fast-growing plants.",
        "Audit fertiliser routine and vacuum substrate.",
    ],
    "ph": [
        "pH is high (>8.0): perform partial water change with neutral water.",
        "Adjust buffering until pH remains within 6.5–8.0.",
    ],
    "kh": [
        "KH is high (>8 dKH): pause buffering additives and top-off with softer water.",
    ],
    "gh": [
        "GH is high (>10 dGH): partial change with RO/soft water; pause GH salts.",
    ],
    "co2_indicator": [
        "CO₂ too high – reduce injection and increase aeration.",
    ],
}

# ──────────────────────────────────────────────────────────────
# Drop-checker colour advice
# ──────────────────────────────────────────────────────────────
CO2_COLOR_ADVICE: dict[str, str] = {
    "Blue":   "CO₂ low – raise injection rate.",
    "Green":  "CO₂ ideal – no action.",
    "Yellow": "CO₂ high – reduce injection / add aeration.",
}

# ──────────────────────────────────────────────────────────────
# Localization (US English)
# ──────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────
# Unit systems
# ──────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────
# Simple conversions
# ──────────────────────────────────────────────────────────────
CONVERSIONS: dict[tuple[str, str], Callable[[float], float]] = {
    ("°C", "°F"): lambda c: c * 9 / 5 + 32,
    ("°F", "°C"): lambda f: (f - 32) * 5 / 9,
}

# ──────────────────────────────────────────────────────────────
# Legacy helper wrappers
# ──────────────────────────────────────────────────────────────
def is_too_low(param: str, value: float) -> bool:
    return TOO_LOW_THRESHOLDS.get(param, float('inf')) > value

def is_too_high(param: str, value: float) -> bool:
    return value > TOO_HIGH_THRESHOLDS.get(param, -float('inf'))

def get_low_action_plan(param: str) -> list[str]:
    return list(LOW_ACTION_PLANS.get(param, []))

def get_high_action_plan(param: str) -> list[str]:
    return list(ACTION_PLANS.get(param, []))


# ──────────────────────────────────────────────────────────────
# Weekly email schedule and SMTP settings
# ──────────────────────────────────────────────────────────────
WEEKLY_EMAIL_TIME: dict[str, Any] = {
    # Scheduler: day_of_week can be 'mon', 'tue', ... or comma-separated
    'day_of_week': 'mon',
    'hour': 9,
    'minute': 0,

    # Email envelope
    'from_address': 'your_email@example.com',

    # SMTP server config
    'smtp': {
        'host': 'smtp.example.com',
        'port': 587,
        'tls': True,
        'username': 'smtp_user',
        'password': 'smtp_password',
    },
}

# ──────────────────────────────────────────────────────────────
# App version & release notes
# ──────────────────────────────────────────────────────────────
VERSION = "v3.7.1"
RELEASE_NOTES = """
### v3.7.1 (2025-06-12)
* **Fix:** Database now persists to `aqualog.db` on disk.
* **Fix:** `init_tables()` called at startup to initialize/migrate schema.
"""