# aqualog_db/repositories/maintenance.py

"""
maintenance.py – Maintenance Data Repository

Handles all database operations for the `maintenance_log` and `maintenance_cycles` tables.
This includes recording completed maintenance tasks, managing recurring maintenance schedules,
and retrieving historical maintenance data.
"""

import sqlite3
from typing import List, Dict, Optional, Any
from ..base import BaseRepository
from ..connection import get_connection

class MaintenanceRepository(BaseRepository):
    """
    Manages database interactions for aquarium maintenance records and schedules.

    Provides methods to save, retrieve, and delete individual maintenance log entries
    as well as recurring maintenance cycles.
    """

    def save_maintenance(
        self,
        *, # Enforce keyword-only arguments for clarity
        tank_id: int,
        date: str,
        m_type: str,
        description: Optional[str],
        volume_changed: Optional[float],
        cost: Optional[float],
        notes: Optional[str],
        next_due: Optional[str],
        cycle_id: Optional[int] = None
    ) -> None:
        """
        Inserts a new maintenance log record into the database.

        Args:
            tank_id: The ID of the tank for which the maintenance was performed.
            date: The date of the maintenance in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
            m_type: The type of maintenance performed (e.g., "Water Change", "Filter Cleaning").
            description: An optional detailed description of the maintenance.
            volume_changed: Optional percentage of water changed (e.g., 25.0, 50.0).
            cost: Optional cost associated with the maintenance.
            notes: Optional additional notes about the maintenance.
            next_due: Optional calculated next due date for the maintenance (ISO format).
            cycle_id: Optional ID of the associated maintenance cycle, if it's part of one.

        Raises:
            sqlite3.Error: If a database error occurs during insertion.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maintenance_log (
                    tank_id, date, maintenance_type, description,
                    volume_changed, cost, notes, next_due, cycle_id
                ) VALUES (?,?,?,?,?,?,?,?,?);
                """,
                (
                    tank_id,
                    date,
                    m_type.strip(), # Ensure type is stripped of whitespace
                    description.strip() if description else None, # Store None if empty string
                    volume_changed,
                    cost,
                    notes.strip() if notes else None, # Store None if empty string
                    next_due,
                    cycle_id
                ),
            )
            conn.commit()

    def get_maintenance(self, *, tank_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all maintenance log entries for a specific tank,
        ordered from most recent to oldest.

        Includes the name of the associated cycle if available.

        Args:
            tank_id: The ID of the tank to fetch maintenance records for.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a maintenance log entry.
                                  Returns an empty list if no records are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
        """
        with get_connection() as conn:
            # Set row_factory to sqlite3.Row for dict-like access
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.*, c.maintenance_type as cycle_name
                  FROM maintenance_log m
                  LEFT JOIN maintenance_cycles c ON m.cycle_id = c.id -- Join to get cycle name
                 WHERE m.tank_id = ?
              ORDER BY m.date DESC, m.id DESC; -- Order by date (desc) then ID for consistent ordering
                """,
                (tank_id,),
            ).fetchall()
        return [dict(r) for r in rows] # Convert sqlite3.Row objects to dictionaries

    def delete_maintenance(self, record_id: int) -> None:
        """
        Deletes a specific maintenance log entry by its ID.

        Args:
            record_id: The unique identifier of the maintenance record to delete.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_log WHERE id = ?;", (record_id,))
            conn.commit()

    def fetch_maintenance_cycles(self, tank_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all maintenance cycles defined for a specific tank.

        Args:
            tank_id: The ID of the tank to fetch maintenance cycles for.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a maintenance cycle.
                                  Returns an empty list if no cycles are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
        """
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

    def save_maintenance_cycle(
        self,
        *, # Enforce keyword-only arguments
        tank_id: int,
        maintenance_type: str,
        frequency_days: int,
        description: Optional[str],
        notes: Optional[str],
        is_active: bool = True
    ) -> None:
        """
        Inserts a new recurring maintenance cycle record into the database.

        Args:
            tank_id: The ID of the tank to which this cycle applies.
            maintenance_type: The type of recurring maintenance (e.g., "Weekly Water Change").
            frequency_days: The frequency of the cycle in days (e.g., 7 for weekly).
            description: An optional detailed description of the cycle.
            notes: Optional additional notes about the cycle.
            is_active: Boolean indicating if the cycle is currently active. Defaults to True.

        Raises:
            sqlite3.Error: If a database error occurs during insertion.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maintenance_cycles (
                    tank_id, maintenance_type, frequency_days,
                    description, notes, is_active
                ) VALUES (?,?,?,?,?,?);
                """,
                (
                    tank_id,
                    maintenance_type.strip(),
                    frequency_days,
                    description.strip() if description else None,
                    notes.strip() if notes else None,
                    is_active
                ),
            )
            conn.commit()

    def delete_maintenance_cycle(self, cycle_id: int) -> None:
        """
        Deletes a specific maintenance cycle by its ID.

        Note: Associated entries in `maintenance_log` will have their `cycle_id`
        set to NULL due to the `ON DELETE SET NULL` foreign key constraint.

        Args:
            cycle_id: The unique identifier of the maintenance cycle to delete.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_cycles WHERE id = ?;", (cycle_id,))
            conn.commit()