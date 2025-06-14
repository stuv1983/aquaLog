"""
legacy.py - Backward compatibility layer
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from .repositories import (
    TankRepository,
    WaterTestRepository,
    CustomRangeRepository,
    EmailSettingsRepository
)
from .schema import SchemaManager

# Initialize repository instances
_tank_repo = TankRepository()
_water_test_repo = WaterTestRepository()
_custom_range_repo = CustomRangeRepository()
_email_settings_repo = EmailSettingsRepository()
_schema_manager = SchemaManager()

# ---------------------------------------------------------------------------
# Schema functions
# ---------------------------------------------------------------------------

def init_tables() -> None:
    """Initialize database tables."""
    _schema_manager.init_tables()

# ---------------------------------------------------------------------------
# Tank functions
# ---------------------------------------------------------------------------

def fetch_all_tanks() -> List[Dict[str, Any]]:
    """Fetch all tanks."""
    return _tank_repo.fetch_all()

def add_tank(name: str, volume_l: Optional[float] = None, notes: str = "") -> Dict[str, Any]:
    """Add a new tank and return its information."""
    return _tank_repo.add(name, volume_l, notes)

def rename_tank(tank_id: int, new_name: str) -> Dict[str, Any]:
    """Rename a tank and return its updated information."""
    return _tank_repo.rename(tank_id, new_name)

def remove_tank(tank_id: int) -> None:
    """Delete a tank."""
    _tank_repo.remove(tank_id)

def update_tank_volume(tank_id: int, volume_l: float) -> Dict[str, Any]:
    """Update a tank's volume and return its updated information."""
    return _tank_repo.update_volume(tank_id, volume_l)

def get_tank(tank_id: int) -> Optional[Dict[str, Any]]:
    """Get a tank by its ID."""
    return _tank_repo.get_by_id(tank_id)

# ---------------------------------------------------------------------------
# Water-test functions
# ---------------------------------------------------------------------------

def save_water_test(data: dict, tank_id: int = 1) -> Dict[str, Any]:
    """Save a water test and return the saved record."""
    return _water_test_repo.save(data, tank_id)


def fetch_data(start: str, end: str, tank_id: Optional[int] = None) -> pd.DataFrame:
    """
    Fetch water tests within a date range and ensure the “date” column is
    parsed to datetime64[ns] so Arrow/Streamlit never chokes on strings.
    """
    df = _water_test_repo.fetch_by_date_range(start, end, tank_id)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


def get_latest_test() -> Optional[Dict[str, Any]]:
    """Get the most recent water test."""
    return _water_test_repo.get_latest()


def get_latest_test_for_tank(tank_id: int) -> Optional[Dict[str, Any]]:
    """Get the most recent water test for a specific tank."""
    return _water_test_repo.get_latest_for_tank(tank_id)

# ---------------------------------------------------------------------------
# Custom Range functions
# ---------------------------------------------------------------------------

def get_custom_range(tank_id: int, parameter: str) -> Optional[Tuple[float, float]]:
    """Get custom range for a tank and parameter."""
    return _custom_range_repo.get(tank_id, parameter)

def set_custom_range(tank_id: int, parameter: str, low: float, high: float) -> Dict[str, Any]:
    """Set or update a custom range and return the saved record."""
    return _custom_range_repo.set(tank_id, parameter, low, high)

def get_all_custom_ranges(tank_id: int) -> Dict[str, Tuple[float, float]]:
    """Get all custom ranges for a tank."""
    return _custom_range_repo.get_all_for_tank(tank_id)

# ---------------------------------------------------------------------------
# Email Settings functions
# ---------------------------------------------------------------------------

def get_user_email_settings() -> Optional[Dict[str, Any]]:
    """Get email settings for the default user."""
    return _email_settings_repo.get()

def save_user_email_settings(**kwargs: Any) -> Dict[str, Any]:
    """Save email settings and return the saved record."""
    return _email_settings_repo.save(**kwargs)
