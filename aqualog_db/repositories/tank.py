# aqualog_db/repositories/tank.py

"""
tank.py – Tank Data Repository

Handles all database operations (Create, Read, Update, Delete) related to the
`tanks` table. Includes functions for adding, renaming, deleting, and querying
tank information, ensuring data integrity through validation.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime # Imported for type hinting, though not directly used in this snippet
from ..base import BaseRepository
import sqlite3 # Imported for specific SQLite exception types

class TankRepository(BaseRepository):
    """
    Manages database interactions for the `tanks` table.

    Provides methods to perform CRUD operations on tank records, including
    data validation to ensure consistency and integrity.
    """
    
    def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Fetches all tank records from the database.

        Includes creation and update timestamps.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents a tank record. Returns an empty list
                                  if no tanks are found.

        Raises:
            RuntimeError: If a database error occurs during fetching.
        """
        return super().fetch_all("""
            SELECT id, name, volume_l, start_date, notes, 
                   datetime(created_at) as created_at,
                   datetime(updated_at) as updated_at
            FROM tanks 
            ORDER BY id;
        """)

    def add(self, name: str, volume_l: Optional[float] = None, notes: str = "") -> Dict[str, Any]:
        """
        Adds a new tank record to the database.

        Args:
            name: The name of the new tank. Must be a non-empty string.
            volume_l: The volume of the tank in liters, optional. Must be non-negative.
            notes: Optional notes for the tank.

        Returns:
            Dict[str, Any]: A dictionary representing the newly created tank record.

        Raises:
            ValueError: If input validation fails (e.g., empty name, negative volume).
            RuntimeError: If a database error occurs during insertion.
        """
        self._validate_tank_input(name, volume_l)
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO tanks (name, volume_l, notes) 
                    VALUES (?,?,?);
                    """,
                    (name.strip(), volume_l, notes.strip())
                )
                inserted_id = cursor.lastrowid # Get the ID of the newly inserted row
                new_tank = self.fetch_one( # Fetch the complete new record
                    "SELECT * FROM tanks WHERE id = ?;",
                    (inserted_id,)
                )
                conn.commit()
                return new_tank
            except sqlite3.IntegrityError as e:
                conn.rollback() # Rollback changes on integrity error
                if "CHECK" in str(e):
                    # Catch specific SQLite CHECK constraint violations
                    raise ValueError(f"Invalid tank data: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback() # Rollback changes on any other SQLite error
                raise RuntimeError(f"Database error: {str(e)}") from e

    def rename(self, tank_id: int, new_name: str) -> Dict[str, Any]:
        """
        Renames an existing tank in the database.

        Args:
            tank_id: The ID of the tank to rename.
            new_name: The new name for the tank. Must be a non-empty string.

        Returns:
            Dict[str, Any]: A dictionary representing the updated tank record.

        Raises:
            ValueError: If `tank_id` is invalid or `new_name` is empty.
            RuntimeError: If a database error occurs during the update.
        """
        self._validate_tank_id(tank_id)
        self._validate_name(new_name)
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE tanks SET name = ? WHERE id = ?;",
                    (new_name.strip(), tank_id)
                )
                updated_tank = self.fetch_one( # Fetch the complete updated record
                    "SELECT * FROM tanks WHERE id = ?;",
                    (tank_id,)
                )
                conn.commit()
                return updated_tank
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid tank name: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def remove(self, tank_id: int) -> None:
        """
        Deletes a tank and all its related records (e.g., water tests, owned fish/plants)
        from the database due to CASCADE foreign key constraints.

        Args:
            tank_id: The ID of the tank to remove.

        Raises:
            ValueError: If `tank_id` is invalid.
            RuntimeError: If a database error occurs during deletion.
        """
        self._validate_tank_id(tank_id)
        
        with self._connection() as conn:
            try:
                conn.execute("DELETE FROM tanks WHERE id = ?;", (tank_id,))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def update_volume(self, tank_id: int, volume_l: float) -> Dict[str, Any]:
        """
        Updates the volume of an existing tank.

        Args:
            tank_id: The ID of the tank to update.
            volume_l: The new volume for the tank in liters. Must be a non-negative number.

        Returns:
            Dict[str, Any]: A dictionary representing the updated tank record.

        Raises:
            ValueError: If `tank_id` is invalid or `volume_l` is not a non-negative number.
            RuntimeError: If a database error occurs during the update.
        """
        self._validate_tank_id(tank_id)
        
        if not isinstance(volume_l, (int, float)) or volume_l < 0:
            raise ValueError("Tank volume must be a non-negative number")
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE tanks SET volume_l = ? WHERE id = ?;",
                    (float(volume_l), tank_id)
                )
                updated_tank = self.fetch_one( # Fetch the complete updated record
                    "SELECT * FROM tanks WHERE id = ?;",
                    (tank_id,)
                )
                conn.commit()
                return updated_tank
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def get_by_id(self, tank_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single tank record by its ID.

        Args:
            tank_id: The ID of the tank to retrieve.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the tank record,
                                      or None if no tank with the given ID is found.

        Raises:
            ValueError: If `tank_id` is invalid.
            RuntimeError: If a database error occurs during fetching.
        """
        self._validate_tank_id(tank_id)
        return self.fetch_one(
            "SELECT * FROM tanks WHERE id = ?;",
            (tank_id,)
        )

    def _validate_tank_input(self, name: str, volume_l: Optional[float]):
        """
        Internal helper method to validate common tank input parameters.

        Args:
            name: The name of the tank.
            volume_l: The volume of the tank in liters.

        Raises:
            ValueError: If `name` is empty or `volume_l` is not a non-negative number (if provided).
        """
        self._validate_name(name)
        
        if volume_l is not None:
            if not isinstance(volume_l, (int, float)) or volume_l < 0:
                raise ValueError("Tank volume must be None or a non-negative number")

    def _validate_name(self, name: str):
        """
        Internal helper method to validate a tank name.

        Args:
            name: The tank name string to validate.

        Raises:
            ValueError: If `name` is not a string, is empty, or contains only whitespace.
        """
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Tank name must be a non-empty string")

    def _validate_tank_id(self, tank_id: int):
        """
        Internal helper method to validate a tank ID.

        Args:
            tank_id: The tank ID to validate.

        Raises:
            ValueError: If `tank_id` is not an integer or is not positive.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")