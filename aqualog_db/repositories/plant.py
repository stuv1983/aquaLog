# aqualog_db/repositories/plant.py
from __future__ import annotations # Added for type hinting consistency
import pandas as pd
from typing import Dict, Any, Optional, TypedDict # Added TypedDict
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

# Define a TypedDict for the structure of a plant record
class PlantRecord(TypedDict, total=False):
    """Represents a single row/record from the `plants` table."""
    plant_id: int
    plant_name: str
    origin: Optional[str]
    origin_info: Optional[str]
    growth_rate: Optional[str]
    growth_info: Optional[str]
    height_cm: Optional[str]
    height_info: Optional[str]
    light_demand: Optional[str]
    light_info: Optional[str]
    co2_demand: Optional[str]
    co2_info: Optional[str]
    thumbnail_url: Optional[str]
    created_at: str
    updated_at: str

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
                          Columns typically include: `plant_id`, `plant_name`, `origin`,
                          `origin_info`, `growth_rate`, `growth_info`, `height_cm`,
                          `height_info`, `light_demand`, `light_info`, `co2_demand`,
                          `co2_info`, `thumbnail_url`, `created_at`, `updated_at`.
                          Returns an empty DataFrame if no plants are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM plants ORDER BY plant_name COLLATE NOCASE", conn)

    def add_plant(self, plant_data: PlantRecord) -> None: # Updated type hint
        """
        Adds a new plant species record to the master `plants` table.

        Args:
            plant_data (PlantRecord): A dictionary containing the data for the new plant.
                                        Expected keys and their typical types are:
                                        - `plant_name` (str): Scientific or common name of the plant.
                                        - `origin` (str, optional): Geographical origin.
                                        - `origin_info` (str, optional): Additional info about origin.
                                        - `growth_rate` (str, optional): e.g., "Slow", "Medium", "High".
                                        - `growth_info` (str, optional): Additional info about growth.
                                        - `height_cm` (str, optional): Expected height in cm (e.g., "5 - 15+").
                                        - `height_info` (str, optional): Additional info about height.
                                        - `light_demand` (str, optional): e.g., "Low", "Medium", "High".
                                        - `light_info` (str, optional): Additional info about light.
                                        - `co2_demand` (str, optional): e.g., "Low", "Medium", "High".
                                        - `co2_info` (str, optional): Additional info about CO2.
                                        - `thumbnail_url` (str, optional): URL to a thumbnail image.

        Raises:
            sqlite3.IntegrityError: If a plant with the same primary key (`plant_id`)
                                    or a unique constraint (e.g., `plant_name` if unique) already exists.
            sqlite3.Error: If a general database error occurs during insertion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            # Dynamically build columns and placeholders from the provided dictionary keys.
            columns = ', '.join(plant_data.keys())
            placeholders = ', '.join('?' for _ in plant_data)
            sql = f"INSERT INTO plants ({columns}) VALUES ({placeholders})"
            
            # Execute the insert operation
            conn.execute(sql, tuple(plant_data.values()))
            conn.commit()