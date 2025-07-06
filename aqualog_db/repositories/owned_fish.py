# aqualog_db/repositories/owned_fish.py

"""
owned_fish.py – Owned Fish Data Repository

Handles all database operations for the `owned_fish` table. This includes
adding fish to a tank's inventory, retrieving fish details for a specific tank,
and removing fish from a tank.
"""

from __future__ import annotations
import pandas as pd
from typing import Optional
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3

class OwnedFishRepository(BaseRepository):
    """
    Manages database interactions for `owned_fish` records, which link
    master fish species to specific tanks in the user's inventory.
    """

    def add_to_tank(self, fish_id: int, tank_id: int, quantity: int = 1) -> None:
        """
        Adds a fish species to a tank's inventory or updates its quantity.
        If the fish already exists, its quantity is increased.

        Args:
            fish_id (int): The ID of the fish species from the master `fish` table.
            tank_id (int): The ID of the tank to which the fish is being added.
            quantity (int): The number of fish to add.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO owned_fish (fish_id, tank_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(fish_id, tank_id) DO UPDATE SET
                quantity = quantity + excluded.quantity;
                """,
                (fish_id, tank_id, quantity)
            )
            conn.commit()

    def update_quantity(self, owned_fish_id: int, quantity: int) -> None:
        """
        Updates the quantity of a specific fish in a tank.

        Args:
            owned_fish_id (int): The unique identifier of the owned fish record.
            quantity (int): The new quantity for the fish.
        """
        with get_connection() as conn:
            conn.execute(
                "UPDATE owned_fish SET quantity = ? WHERE id = ?",
                (quantity, owned_fish_id)
            )
            conn.commit()

    def fetch_for_tank_with_details(self, tank_id: int) -> pd.DataFrame:
        """
        Fetches all fish records for a given tank, including detailed information
        from the master `fish` table.

        Args:
            tank_id (int): The ID of the tank whose owned fish records are to be fetched.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the owned fish records.
        """
        with get_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT
                    o.id as owned_fish_id,
                    o.quantity,
                    p.*
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
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM owned_fish WHERE id = ?", (owned_fish_id,))
            conn.commit()