# aqualog_db/repositories/plant.py
import pandas as pd
from typing import Dict, Any
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

class PlantRepository(BaseRepository):
    """
    Manages database interactions for the master `plants` table, which stores
    information about various aquatic plant species.
    """

    def fetch_all(self) -> pd.DataFrame:
        """
        Fetches all plant species records from the master `plants` table.

        The results are ordered alphabetically by plant name.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing all plant records.
                          Returns an empty DataFrame if no plants are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
        """
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM plants ORDER BY plant_name COLLATE NOCASE", conn)

    def add_plant(self, plant_data: Dict[str, Any]) -> None:
        """
        Adds a new plant species record to the master `plants` table.

        Args:
            plant_data: A dictionary containing the data for the new plant.
                        Expected keys include 'plant_name', 'origin', 'growth_rate',
                        'height_cm', 'light_demand', 'co2_demand', 'thumbnail_url'.

        Raises:
            sqlite3.IntegrityError: If a plant with the same primary key (plant_id)
                                    or unique constraint (plant_name) already exists.
            sqlite3.Error: If a general database error occurs during insertion.
        """
        with get_connection() as conn:
            # Dynamically build columns and placeholders from the provided dictionary keys.
            columns = ', '.join(plant_data.keys())
            placeholders = ', '.join('?' for _ in plant_data)
            sql = f"INSERT INTO plants ({columns}) VALUES ({placeholders})"
            
            # Execute the insert operation
            conn.execute(sql, tuple(plant_data.values()))
            conn.commit()