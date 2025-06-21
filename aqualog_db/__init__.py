# aqualog_db/__init__.py (Updated)

"""
aqualog_db — Top-level API for AquaLog’s database layer.
Exposes repository classes for all data operations.
"""

import logging # New import

# 1. Import SchemaManager instead of legacy functions
from .schema import SchemaManager
from .repositories import (
    TankRepository,
    WaterTestRepository,
    CustomRangeRepository,
    EmailSettingsRepository,
)

# Configure a basic logger for the aqualog_db package
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Define a clean init_tables function using the modern pattern
def init_tables():
    """Initializes all database tables, indexes, and triggers."""
    try:
        SchemaManager().init_tables()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)


# 3. Update __all__ to export only the modern components
__all__ = [
    "init_tables",
    "TankRepository",
    "WaterTestRepository",
    "CustomRangeRepository",
    "EmailSettingsRepository",
]