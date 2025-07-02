# aqualog_db/repositories/tank.py

"""
tank.py – Tank Data Repository

Handles all database operations (Create, Read, Update, Delete) related to the
`tanks` table. Includes functions for adding, renaming, deleting, and querying
tank information, ensuring data integrity through validation.
"""

from __future__ import annotations # Added for type hinting consistency

from typing import List, Dict, Optional, Any, Tuple, TypedDict
from datetime import datetime # Imported for type hinting, though not directly used in this snippet
from ..base import BaseRepository
import sqlite3 # Imported for specific SQLite exception types

# Define a TypedDict for the structure of a tank record
class TankRecord(TypedDict, total=False):
    """Represents a single row/record from the `tanks` table."""
    id: int
    name: str
    volume_l: Optional[float]
    start_date: Optional[str]
    notes: Optional[str]
    has_co2: bool
    co2_on_hour: Optional[int]
    co2_off_hour: Optional[int]
    created_at: str
    updated_at: str

class TankRepository(BaseRepository):
    """
    Manages database interactions for the `tanks` table.

    Provides methods to perform CRUD operations on tank records, including
    data validation to ensure consistency and integrity.
    """
    
    def fetch_all(self) -> List[TankRecord]:
        """
        Fetches all tank records from the database.

        Includes creation and update timestamps.
        The results are ordered by tank ID.

        Returns:
            List[TankRecord]: A list of dictionaries, where each dictionary
                                  represents a tank record.
        """
        return [TankRecord(r) for r in super().fetch_all("""
            SELECT id, name, volume_l, start_date, notes, has_co2, co2_on_hour, co2_off_hour,
                   datetime(created_at) as created_at,
                   datetime(updated_at) as updated_at
            FROM tanks 
            ORDER BY id;
        """)]

    def add(self, name: str, volume_l: Optional[float] = None, *, has_co2: bool = True, notes: str = "") -> TankRecord:
        """
        Adds a new tank record to the database.

        Args:
            name (str): The name of the new tank. Must be a non-empty string.
            volume_l (Optional[float]): The volume of the tank in liters, optional.
            has_co2 (bool): Flag indicating if the tank uses CO2 injection.
            notes (str): Optional notes for the tank.

        Returns:
            TankRecord: A dictionary representing the newly created tank record.

        Raises:
            ValueError: If input validation fails.
            RuntimeError: If a database error occurs.
        """
        self._validate_tank_input(name, volume_l)
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO tanks (name, volume_l, notes, has_co2) 
                    VALUES (?,?,?,?);
                    """,
                    (name.strip(), volume_l, notes.strip() if notes else None, has_co2)
                )
                inserted_id = cursor.lastrowid
                new_tank = self.fetch_one(
                    "SELECT * FROM tanks WHERE id = ?;",
                    (inserted_id,)
                )
                conn.commit()
                return TankRecord(new_tank) if new_tank else None
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid tank data: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def rename(self, tank_id: int, new_name: str) -> TankRecord:
        """
        Renames an existing tank in the database.
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
                updated_tank = self.fetch_one(
                    "SELECT * FROM tanks WHERE id = ?;",
                    (tank_id,)
                )
                conn.commit()
                return TankRecord(updated_tank) if updated_tank else None
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
        Deletes a tank and all its related records from the database.
        """
        self._validate_tank_id(tank_id)
        
        with self._connection() as conn:
            try:
                conn.execute("DELETE FROM tanks WHERE id = ?;", (tank_id,))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def update_volume(self, tank_id: int, volume_l: float) -> TankRecord:
        """
        Updates the volume of an existing tank.
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
                updated_tank = self.fetch_one(
                    "SELECT * FROM tanks WHERE id = ?;",
                    (tank_id,)
                )
                conn.commit()
                return TankRecord(updated_tank) if updated_tank else None
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def set_co2_schedule(self, tank_id: int, on_hour: Optional[int], off_hour: Optional[int]) -> TankRecord:
        """
        Sets the custom CO2 ON and OFF hours for a specific tank.
        """
        self._validate_tank_id(tank_id)
        if on_hour is not None and not (0 <= on_hour <= 23):
            raise ValueError("CO2 ON hour must be between 0 and 23.")
        if off_hour is not None and not (0 <= off_hour <= 23):
            raise ValueError("CO2 OFF hour must be between 0 and 23.")
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE tanks SET co2_on_hour = ?, co2_off_hour = ? WHERE id = ?;",
                    (on_hour, off_hour, tank_id)
                )
                updated_tank = self.fetch_one(
                    "SELECT * FROM tanks WHERE id = ?;",
                    (tank_id,)
                )
                conn.commit()
                return TankRecord(updated_tank) if updated_tank else None
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def set_co2_status(self, tank_id: int, has_co2: bool) -> None:
        """
        Sets the CO2 usage status for a specific tank.
        """
        self._validate_tank_id(tank_id)
        
        with self._connection() as conn:
            try:
                conn.execute(
                    "UPDATE tanks SET has_co2 = ? WHERE id = ?;",
                    (has_co2, tank_id)
                )
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e


    def get_by_id(self, tank_id: int) -> Optional[TankRecord]:
        """
        Retrieves a single tank record by its ID.
        """
        self._validate_tank_id(tank_id)
        result = self.fetch_one(
            "SELECT * FROM tanks WHERE id = ?;",
            (tank_id,)
        )
        return TankRecord(result) if result else None

    def _validate_tank_input(self, name: str, volume_l: Optional[float]) -> None:
        """
        Internal helper method to validate common tank input parameters for creation.
        """
        self._validate_name(name)
        
        if volume_l is not None:
            if not isinstance(volume_l, (int, float)) or volume_l < 0:
                raise ValueError("Tank volume must be None or a non-negative number")

    def _validate_name(self, name: str) -> None:
        """
        Internal helper method to validate a tank name.
        """
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Tank name must be a non-empty string")

    def _validate_tank_id(self, tank_id: int) -> None:
        """
        Internal helper method to validate a tank ID.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")