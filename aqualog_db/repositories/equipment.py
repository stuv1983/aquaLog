# aqualog_db/repositories/equipment.py

"""
equipment.py – Equipment Data Repository

Handles all database operations for the `equipment` table.
"""
import pandas as pd
from typing import List, Optional
from ..base import BaseRepository
from ..connection import get_connection

class EquipmentRepository(BaseRepository):
    """Handles all equipment-related database operations."""

    def add_equipment(self, name: str, category: str, purchase_date: str, notes: Optional[str], tank_id: int) -> None:
        """Add a new piece of equipment to the database."""
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO equipment (name, category, purchase_date, notes, tank_id)
                VALUES (?,?,?,?,?);
                """,
                (
                    name.strip(),
                    category,
                    purchase_date,
                    notes.strip() if notes else None,
                    tank_id,
                ),
            )
            conn.commit()

    def fetch_for_tank(self, tank_id: int) -> pd.DataFrame:
        """Fetch all equipment for a given tank."""
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
        """Remove one or more pieces of equipment from the database."""
        with get_connection() as conn:
            conn.executemany(
                "DELETE FROM equipment WHERE equipment_id = ? AND tank_id = ?;",
                [(eid, tank_id) for eid in equipment_ids],
            )
            conn.commit()