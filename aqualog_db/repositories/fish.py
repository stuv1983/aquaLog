# aqualog_db/repositories/fish.py

"""
fish.py – Fish Data Repository

Handles all database operations for the master `fish` table. This includes
fetching the entire catalogue of fish species and adding new species to it.
"""

from __future__ import annotations # Added for type hinting consistency

import pandas as pd
from typing import Dict, Any, Optional, TypedDict # Added TypedDict for more specific type hints
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

# Define a TypedDict for the structure of a fish record
class FishRecord(TypedDict, total=False):
    """Represents a single row/record from the `fish` table."""
    fish_id: int
    species_name: str
    common_name: Optional[str]
    origin: Optional[str]
    phmin: Optional[float]
    phmax: Optional[float]
    temperature_min: Optional[float]
    temperature_max: Optional[float]
    tank_size_liter: Optional[float]
    image_url: Optional[str]
    swim: Optional[int]

class FishRepository(BaseRepository):
    """
    Manages database interactions for the master `fish` table, which stores
    information about various fish species and their environmental requirements.
    """

    def fetch_all(self) -> pd.DataFrame:
        """
        Fetches all fish species records from the master `fish` table.

        The results are ordered alphabetically by species name (scientific name).

        Returns:
            pd.DataFrame: A Pandas DataFrame containing all fish records.
                          Columns typically include: `fish_id`, `species_name`,
                          `common_name`, `origin`, `phmin`, `phmax`,
                          `temperature_min`, `temperature_max`, `tank_size_liter`,
                          `image_url`, `swim`.
                          Returns an empty DataFrame if no fish are found.

        Raises:
            sqlite3.Error: If a database error occurs during the fetch operation.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM fish ORDER BY species_name COLLATE NOCASE", conn)

    def add_fish(self, fish_data: FishRecord) -> None: # Updated type hint to FishRecord
        """
        Adds a new fish species record to the master `fish` table.

        Args:
            fish_data (FishRecord): A dictionary (TypedDict) containing the data for the new fish.
                                        Expected keys and their typical types are:
                                        - `species_name` (str): Scientific name (e.g., "Pterophyllum scalare").
                                        - `common_name` (str, optional): Common name (e.g., "Angelfish").
                                        - `origin` (str, optional): Geographical origin.
                                        - `phmin` (float, optional): Minimum pH tolerance.
                                        - `phmax` (float, optional): Maximum pH tolerance.
                                        - `temperature_min` (float, optional): Minimum temperature tolerance in Celsius.
                                        - `temperature_max` (float, optional): Maximum temperature tolerance in Celsius.
                                        - `tank_size_liter` (float, optional): Minimum tank size in liters for this species.
                                        - `image_url` (str, optional): URL to an image of the fish.
                                        - `swim` (int, optional): Swim level (e.g., 1=bottom, 2=mid, 3=top).

        Raises:
            sqlite3.IntegrityError: If a fish with the same primary key (`fish_id`)
                                    or unique constraint (`species_name`) already exists.
            sqlite3.Error: If a general database error occurs during the insertion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            # Dynamically build columns and placeholders from the provided dictionary keys.
            columns = ', '.join(fish_data.keys())
            placeholders = ', '.join('?' for _ in fish_data)
            sql = f"INSERT INTO fish ({columns}) VALUES ({placeholders})"
            
            # Execute the insert operation
            conn.execute(sql, tuple(fish_data.values()))
            conn.commit()