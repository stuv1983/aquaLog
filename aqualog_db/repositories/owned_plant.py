# aqualog_db/repositories/owned_plant.py
from __future__ import annotations # Added for type hinting consistency
import pandas as pd
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

class OwnedPlantRepository(BaseRepository):
    """
    Manages database interactions for `owned_plants` records, which link
    master plant species to specific tanks in the user's inventory.
    """

    def add_to_tank(self, plant_id: int, tank_id: int, common_name: str) -> None:
        """
        Adds a plant species to a specific tank's inventory.

        If the plant species (identified by `plant_id`) already exists in the
        given `tank_id`'s inventory, this operation does nothing due to the
        `ON CONFLICT DO NOTHING` clause on the unique constraint.
        This prevents duplicate entries for the same plant in the same tank.

        Args:
            plant_id (int): The ID of the plant species from the master `plants` table.
            tank_id (int): The ID of the tank to which the plant is being added.
            common_name (str): A user-defined common name for the plant, specific
                               to this owned instance in the tank.

        Raises:
            sqlite3.Error: If a database error occurs during insertion,
                           other than a unique constraint violation (which is ignored).
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO owned_plants (plant_id, common_name, tank_id)
                VALUES (?, ?, ?) ON CONFLICT(plant_id, tank_id) DO NOTHING
            """,
                (plant_id, common_name, tank_id)
            )
            conn.commit()

    def fetch_for_tank(self, tank_id: int) -> pd.DataFrame:
        """
        Fetches all plant records for a given tank, including detailed information
        from the master `plants` table.

        It prioritizes the `common_name` stored in `owned_plants` for display,
        falling back to `plant_name` from the master `plants` table if the common
        name is empty or `NULL`. Results are ordered alphabetically by the chosen display name.

        Args:
            tank_id (int): The ID of the tank whose owned plant records are to be fetched.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the owned plant records
                          with their full details. Columns typically include all columns
                          from the `plants` table (e.g., `plant_id`, `plant_name`,
                          `origin`, `growth_rate`, `height_cm`, `light_demand`,
                          `co2_demand`, `thumbnail_url`) plus a `display_name` column.
                          Returns an empty DataFrame if no plants are found for the tank.

        Raises:
            sqlite3.Error: If a database error occurs during the fetch operation.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT
                    p.*, -- Select all columns from the master plants table
                    COALESCE(NULLIF(o.common_name, ''), p.plant_name) AS display_name
                    -- display_name will be o.common_name if not NULL or empty, else p.plant_name
                FROM owned_plants o
                JOIN plants p ON o.plant_id = p.plant_id
                WHERE o.tank_id = ?
                ORDER BY display_name COLLATE NOCASE
            """,
                conn,
                params=(tank_id,),
            )

    def remove_from_tank(self, plant_id: int, tank_id: int) -> None:
        """
        Removes a specific plant record from a tank's inventory.

        The removal is based on a unique combination of `plant_id` and `tank_id`.

        Args:
            plant_id (int): The ID of the plant species to remove.
            tank_id (int): The ID of the tank from which the plant should be removed.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?",
                (plant_id, tank_id)
            )
            conn.commit()