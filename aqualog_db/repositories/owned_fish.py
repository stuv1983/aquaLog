# aqualog_db/repositories/owned_fish.py

"""
owned_fish.py – Owned Fish Data Repository

Handles all database operations for the `owned_fish` table. This includes
adding fish to a tank's inventory, retrieving fish details for a specific tank,
and removing fish from a tank.
"""

from __future__ import annotations # Added for type hinting consistency

import pandas as pd
from typing import List, Optional
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

class OwnedFishRepository(BaseRepository):
    """
    Manages database interactions for `owned_fish` records, which link
    master fish species to specific tanks in the user's inventory.
    """

    def add_to_tank(self, fish_id: int, tank_id: int) -> None:
        """
        Adds a fish species to a specific tank's inventory.

        If the fish species (identified by `fish_id`) already exists in the
        given `tank_id`'s inventory, this operation does nothing due to the
        `ON CONFLICT DO NOTHING` clause on the unique constraint. The quantity
        for a newly added fish is initialized to 1.

        Args:
            fish_id (int): The ID of the fish species from the master `fish` table.
            tank_id (int): The ID of the tank to which the fish is being added.

        Raises:
            sqlite3.Error: If a database error occurs during insertion,
                           other than a unique constraint violation (which is ignored).
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO owned_fish (fish_id, tank_id, quantity)
                VALUES (?, ?, 1) ON CONFLICT(fish_id, tank_id) DO NOTHING
            """,
                (fish_id, tank_id)
            )
            conn.commit()

    def fetch_for_tank_with_details(self, tank_id: int) -> pd.DataFrame:
        """
        Fetches all fish records for a given tank, including detailed information
        from the master `fish` table.

        The results are ordered alphabetically by the scientific species name.

        Args:
            tank_id (int): The ID of the tank whose owned fish records are to be fetched.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the owned fish records
                          with their full details. Columns typically include:
                          `owned_fish_id` (unique ID for the owned instance), `quantity`,
                          and all columns from the master `fish` table (e.g., `fish_id`,
                          `species_name`, `common_name`, `phmin`, `phmax`, etc.).
                          Returns an empty DataFrame if no fish are found for the tank.

        Raises:
            sqlite3.Error: If a database error occurs during the fetch operation.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT
                    o.id as owned_fish_id, -- Unique ID for the owned instance
                    o.quantity,
                    p.* -- Select all columns from the master fish table
                FROM owned_fish o
                JOIN fish p ON o.fish_id = p.fish_id
                WHERE o.tank_id = ?
                ORDER BY p.species_name COLLATE NOCASE
            """,
                conn,
                params=(tank_id,),
            )

    def remove_from_tank(self, owned_fish_id: int) -> None:
        """
        Removes a specific owned fish record from a tank's inventory by its
        unique `owned_fish_id`.

        Args:
            owned_fish_id (int): The unique identifier of the owned fish record to delete.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM owned_fish WHERE id = ?", (owned_fish_id,))
            conn.commit()