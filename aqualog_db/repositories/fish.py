# aqualog_db/repositories/fish.py

"""
fish.py – Fish Data Repository

Handles all database operations for the master `fish` table.
"""
import pandas as pd
from typing import Dict, Any
from ..base import BaseRepository
from ..connection import get_connection

class FishRepository(BaseRepository):
    """Handles all master fish list related database operations."""

    def fetch_all(self) -> pd.DataFrame:
        """Fetch all fish from the master list."""
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM fish ORDER BY species_name COLLATE NOCASE", conn)

    def add_fish(self, fish_data: Dict[str, Any]) -> None:
        """Add a new fish to the master list."""
        with get_connection() as conn:
            columns = ', '.join(fish_data.keys())
            placeholders = ', '.join('?' for _ in fish_data)
            sql = f"INSERT INTO fish ({columns}) VALUES ({placeholders})"
            conn.execute(sql, tuple(fish_data.values()))
            conn.commit()