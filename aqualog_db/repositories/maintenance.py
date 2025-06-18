# aqualog_db/repositories/maintenance.py

"""
maintenance.py – Maintenance Data Repository

Handles all database operations for the `maintenance_log` and `maintenance_cycles` tables.
"""

import sqlite3
from typing import List, Dict, Optional, Any
from ..base import BaseRepository
from ..connection import get_connection

class MaintenanceRepository(BaseRepository):
    """Handles all maintenance-related database operations."""

    def save_maintenance(self, *, tank_id: int, date: str, m_type: str, description: Optional[str], volume_changed: Optional[float], cost: Optional[float], notes: Optional[str], next_due: Optional[str], cycle_id: Optional[int] = None) -> None:
        """Insert a maintenance record for the given tank."""
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maintenance_log (
                    tank_id, date, maintenance_type, description,
                    volume_changed, cost, notes, next_due, cycle_id
                ) VALUES (?,?,?,?,?,?,?,?,?);
                """,
                (
                    tank_id, date, m_type.strip(), description.strip() if description else None,
                    volume_changed, cost, notes.strip() if notes else None,
                    next_due, cycle_id
                ),
            )
            conn.commit()

    def get_maintenance(self, *, tank_id: int) -> List[Dict[str, Any]]:
        """Return list of maintenance rows (latest first) for this tank."""
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.*, c.maintenance_type as cycle_name
                  FROM maintenance_log m
                  LEFT JOIN maintenance_cycles c ON m.cycle_id = c.id
                 WHERE m.tank_id = ?
              ORDER BY m.date DESC, m.id DESC;
                """,
                (tank_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_maintenance(self, record_id: int) -> None:
        """Delete a maintenance row by id."""
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_log WHERE id = ?;", (record_id,))
            conn.commit()

    def fetch_maintenance_cycles(self, tank_id: int) -> List[Dict[str, Any]]:
        """Return list of maintenance cycles for this tank."""
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, maintenance_type as type, created_at as date,
                       notes, frequency_days, is_active
                FROM maintenance_cycles
                WHERE tank_id = ?
                ORDER BY datetime(created_at) DESC;
                """,
                (tank_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_maintenance_cycle(self, *, tank_id: int, maintenance_type: str, frequency_days: int, description: Optional[str], notes: Optional[str], is_active: bool = True) -> None:
        """Insert a maintenance cycle record."""
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maintenance_cycles (
                    tank_id, maintenance_type, frequency_days,
                    description, notes, is_active
                ) VALUES (?,?,?,?,?,?);
                """,
                (
                    tank_id, maintenance_type.strip(), frequency_days,
                    description.strip() if description else None,
                    notes.strip() if notes else None, is_active
                ),
            )
            conn.commit()

    def delete_maintenance_cycle(self, cycle_id: int) -> None:
        """Delete a maintenance cycle by id."""
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_cycles WHERE id = ?;", (cycle_id,))
            conn.commit()