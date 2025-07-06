# aqualog_db/repositories/owned_plant.py
from __future__ import annotations
import pandas as pd
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3

class OwnedPlantRepository(BaseRepository):
    """
    Manages database interactions for `owned_plants` records, which link
    master plant species to specific tanks in the user's inventory.
    """

    def add_to_tank(self, plant_id: int, tank_id: int, common_name: str, quantity: int = 1) -> None:
        """
        Adds a plant species to a tank's inventory or updates its quantity.
        If the plant already exists in the tank, its quantity is increased.

        Args:
            plant_id (int): The ID of the plant species from the master `plants` table.
            tank_id (int): The ID of the tank to which the plant is being added.
            common_name (str): A user-defined common name for the plant.
            quantity (int): The number of plants to add.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO owned_plants (plant_id, common_name, tank_id, quantity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(plant_id, tank_id) DO UPDATE SET
                quantity = quantity + excluded.quantity;
                """,
                (plant_id, common_name, tank_id, quantity)
            )
            conn.commit()

    def update_quantity(self, plant_id: int, tank_id: int, quantity: int) -> None:
        """
        Updates the quantity of a specific plant in a tank.

        Args:
            plant_id (int): The ID of the plant species.
            tank_id (int): The ID of the tank.
            quantity (int): The new quantity for the plant.
        """
        with get_connection() as conn:
            conn.execute(
                "UPDATE owned_plants SET quantity = ? WHERE plant_id = ? AND tank_id = ?",
                (quantity, plant_id, tank_id)
            )
            conn.commit()

    def fetch_for_tank(self, tank_id: int) -> pd.DataFrame:
        """
        Fetches all plant records for a given tank, including detailed information
        from the master `plants` table.

        Args:
            tank_id (int): The ID of the tank whose owned plant records are to be fetched.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the owned plant records.
        """
        with get_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT
                    p.*,
                    o.quantity,
                    COALESCE(NULLIF(o.common_name, ''), p.plant_name) AS display_name
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

        Args:
            plant_id (int): The ID of the plant species to remove.
            tank_id (int): The ID of the tank from which the plant should be removed.
        """
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?",
                (plant_id, tank_id)
            )
            conn.commit()