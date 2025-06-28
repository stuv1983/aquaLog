# aqualog_db/repositories/equipment.py

"""
equipment.py – Equipment Data Repository

Handles all database operations for the `equipment` table. This includes
adding new equipment records, fetching equipment associated with a specific tank,
and removing equipment.
"""

from __future__ import annotations # Added for type hinting consistency

import pandas as pd
from typing import List, Optional
from ..base import BaseRepository
from ..connection import get_connection
import sqlite3 # Imported for type hinting sqlite3.Error

class EquipmentRepository(BaseRepository):
    """
    Manages database interactions for the `equipment` table.

    Provides methods to perform CRUD (Create, Read, Delete) operations
    on aquarium equipment records, with each record associated with a specific tank.
    """

    def add_equipment(
        self,
        name: str,
        category: str,
        purchase_date: Optional[str],
        notes: Optional[str],
        tank_id: int
    ) -> None:
        """
        Adds a new piece of equipment to the database for a specific tank.

        Args:
            name (str): The name of the equipment (e.g., "Fluval FX6 Filter").
                        Cannot be empty or whitespace-only.
            category (str): The category of the equipment (e.g., "Filters", "Heater").
            purchase_date (Optional[str]): The date of purchase in ISO format (YYYY-MM-DD),
                                           or `None` if not specified.
            notes (Optional[str]): Any additional notes about the equipment,
                                   or `None` if empty.
            tank_id (int): The ID of the tank this equipment belongs to.

        Raises:
            sqlite3.Error: If a database error occurs during the insertion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO equipment (name, category, purchase_date, notes, tank_id)
                VALUES (?,?,?,?,?);
                """,
                (
                    name.strip(),
                    category,
                    purchase_date, # purchase_date can be None
                    notes.strip() if notes else None, # Store None if notes is empty string or None
                    tank_id,
                ),
            )
            conn.commit()

    def fetch_for_tank(self, tank_id: int) -> pd.DataFrame:
        """
        Fetches all equipment records associated with a given tank.

        The results are ordered first by category, then alphabetically by name.

        Args:
            tank_id (int): The ID of the tank whose equipment records are to be fetched.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the equipment records.
                          Columns typically include: `equipment_id`, `name`,
                          `category`, `purchase_date`, `notes`.
                          Returns an empty DataFrame if no equipment is found for the tank.

        Raises:
            sqlite3.Error: If a database error occurs during the fetch operation.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT equipment_id, name, category, purchase_date, notes
                FROM equipment
                WHERE tank_id = ?
                ORDER BY category, name COLLATE NOCASE;
                """,
                conn,
                params=(tank_id,),
            )

    def remove_equipment(self, equipment_ids: List[int], tank_id: int) -> None:
        """
        Removes one or more pieces of equipment from the database for a specific tank.

        This operation includes `tank_id` in the `WHERE` clause as an extra
        layer of safety to prevent accidental deletion of equipment from
        other tanks.

        Args:
            equipment_ids (List[int]): A list of unique identifiers (`equipment_id`)
                                       of the equipment items to be removed.
            tank_id (int): The ID of the tank from which the equipment should be removed.

        Raises:
            sqlite3.Error: If a database error occurs during the deletion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            # Use executemany for efficient deletion of multiple items
            conn.executemany(
                "DELETE FROM equipment WHERE equipment_id = ? AND tank_id = ?;",
                [(eid, tank_id) for eid in equipment_ids],
            )
            conn.commit()