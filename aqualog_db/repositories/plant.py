# aqualog_db/repositories/plant.py
import pandas as pd
from typing import Dict, Any
import sqlite3
from ..base import BaseRepository
from ..connection import get_connection

class PlantRepository(BaseRepository):
    """Handles all master plant list related database operations."""

    def fetch_all(self) -> pd.DataFrame:
        """Fetch all plants from the master list."""
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM plants ORDER BY plant_name COLLATE NOCASE", conn)

    def add_plant(self, plant_data: Dict[str, Any]) -> None:
        """Add a new plant to the master list."""
        with get_connection() as conn:
            columns = ', '.join(plant_data.keys())
            placeholders = ', '.join('?' for _ in plant_data)
            sql = f"INSERT INTO plants ({columns}) VALUES ({placeholders})"
            conn.execute(sql, tuple(plant_data.values()))
            conn.commit()