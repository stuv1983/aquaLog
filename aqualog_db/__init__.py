# aqualog_db/__init__.py (Updated)

"""
aqualog_db — Top-level API for AquaLog’s database layer.
Exposes repository classes for all data operations.
"""

# 1. Import SchemaManager instead of legacy functions
from .schema import SchemaManager
from .repositories import (
    TankRepository,
    WaterTestRepository,
    CustomRangeRepository,
    EmailSettingsRepository,
)

# 2. Define a clean init_tables function using the modern pattern
def init_tables():
    """Initializes all database tables, indexes, and triggers."""
    SchemaManager().init_tables()

# 3. Update __all__ to export only the modern components
__all__ = [
    "init_tables",
    "TankRepository",
    "WaterTestRepository",
    "CustomRangeRepository",
    "EmailSettingsRepository",
]