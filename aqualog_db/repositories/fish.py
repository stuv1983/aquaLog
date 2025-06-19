# aqualog_db/repositories/fish.py

"""
fish.py – Fish Data Repository

Handles all database operations for the master `fish` table. This includes
fetching the entire catalogue of fish species and adding new species to it.
"""
import pandas as pd
from typing import Dict, Any
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

class FishRepository(BaseRepository):
    """
    Manages database interactions for the master `fish` table, which stores
    information about various fish species and their environmental requirements.
    """

    def fetch_all(self) -> pd.DataFrame:
        """
        Fetches all fish species records from the master `fish` table.

        The results are ordered alphabetically by species name.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing all fish records.
                          Returns an empty DataFrame if no fish are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
        """
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM fish ORDER BY species_name COLLATE NOCASE", conn)

    def add_fish(self, fish_data: Dict[str, Any]) -> None:
        """
        Adds a new fish species record to the master `fish` table.

        Args:
            fish_data: A dictionary containing the data for the new fish.
                       Expected keys include 'species_name', 'common_name', 'origin',
                       'phmin', 'phmax', 'temperature_min', 'temperature_max',
                       'tank_size_liter', 'image_url', 'swim'.

        Raises:
            sqlite3.IntegrityError: If a fish with the same primary key (fish_id)
                                    or unique constraint (species_name) already exists.
            sqlite3.Error: If a general database error occurs during insertion.
        """
        with get_connection() as conn:
            # Dynamically build columns and placeholders from the provided dictionary keys.
            columns = ', '.join(fish_data.keys())
            placeholders = ', '.join('?' for _ in fish_data)
            sql = f"INSERT INTO fish ({columns}) VALUES ({placeholders})"
            
            # Execute the insert operation
            conn.execute(sql, tuple(fish_data.values()))
            conn.commit()