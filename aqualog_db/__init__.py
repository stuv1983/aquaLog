# aqualog_db/__init__.py

"""
aqualog_db — Top-level API for AquaLog’s database layer.
Exposes legacy functions (e.g. init_tables) and repository classes.
"""

from .legacy import init_tables
from .repositories import (
    TankRepository,
    WaterTestRepository,
    CustomRangeRepository,
    EmailSettingsRepository,
)

__all__ = [
    "init_tables",
    "TankRepository",
    "WaterTestRepository",
    "CustomRangeRepository",
    "EmailSettingsRepository",
]
