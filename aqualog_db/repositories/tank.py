# aqualog_db/repositories/tank.py

"""
tank.py – Tank Data Repository

Handles all database operations (Create, Read, Update, Delete) related to the
`tanks` table. Includes functions for adding, renaming, deleting, and querying
tank information.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from ..base import BaseRepository

class TankRepository(BaseRepository):
    """Handles all tank-related database operations with validation."""
    
    def fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch all tanks with their information."""
        return super().fetch_all("""
            SELECT id, name, volume_l, start_date, notes, 
                   datetime(created_at) as created_at,
                   datetime(updated_at) as updated_at
            FROM tanks 
            ORDER BY id;
        """)

    def add(self, name: str, volume_l: Optional[float] = None, notes: str = "") -> Dict[str, Any]:
        """Add a new tank and return its complete information."""
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
                inserted_id = cursor.lastrowid
                new_tank = self.fetch_one(
                    "SELECT * FROM tanks WHERE id = ?;",
                    (inserted_id,)
                )
                conn.commit()
                return new_tank
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid tank data: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def rename(self, tank_id: int, new_name: str) -> Dict[str, Any]:
        """Rename a tank and return its updated information."""
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
        """Delete a tank and all its related records (via CASCADE)."""
        self._validate_tank_id(tank_id)
        
        with self._connection() as conn:
            try:
                conn.execute("DELETE FROM tanks WHERE id = ?;", (tank_id,))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def update_volume(self, tank_id: int, volume_l: float) -> Dict[str, Any]:
        """Update a tank's volume and return its updated information."""
        self._validate_tank_id(tank_id)
        
        if not isinstance(volume_l, (int, float)) or volume_l < 0:
            raise ValueError("Tank volume must be a positive number")
        
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
                return updated_tank
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def get_by_id(self, tank_id: int) -> Optional[Dict[str, Any]]:
        """Get a tank by its ID."""
        self._validate_tank_id(tank_id)
        return self.fetch_one(
            "SELECT * FROM tanks WHERE id = ?;",
            (tank_id,)
        )

    def _validate_tank_input(self, name: str, volume_l: Optional[float]):
        """Validate tank input parameters."""
        self._validate_name(name)
        
        if volume_l is not None:
            if not isinstance(volume_l, (int, float)) or volume_l < 0:
                raise ValueError("Tank volume must be None or a positive number")

    def _validate_name(self, name: str):
        """Validate tank name."""
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Tank name must be a non-empty string")

    def _validate_tank_id(self, tank_id: int):
        """Validate tank ID."""
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")
