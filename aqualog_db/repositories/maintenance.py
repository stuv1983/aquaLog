# aqualog_db/repositories/maintenance.py

"""
maintenance.py – Maintenance Data Repository

Handles all database operations for the `maintenance_log` and `maintenance_cycles` tables.
This includes recording completed maintenance tasks, managing recurring maintenance schedules,
and retrieving historical maintenance data.
"""

from __future__ import annotations # Added for type hinting consistency

import sqlite3
from typing import List, Dict, Optional, Any, TypedDict # Added TypedDict

# Define TypedDicts for structured type hinting of maintenance records
class MaintenanceLogRecord(TypedDict, total=False):
    """Represents a single row/record from the `maintenance_log` table."""
    id: int
    tank_id: int
    cycle_id: Optional[int]
    date: str
    maintenance_type: str
    description: Optional[str]
    volume_changed: Optional[float]
    cost: Optional[float]
    notes: Optional[str]
    next_due: Optional[str]
    is_completed: bool
    created_at: str
    cycle_name: Optional[str] # From JOIN

class MaintenanceCycleRecord(TypedDict, total=False):
    """Represents a single row/record from the `maintenance_cycles` table."""
    id: int
    tank_id: int
    maintenance_type: str
    frequency_days: int
    description: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    type: str # Alias of maintenance_type
    date: str # Alias of created_at

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
            tank_id (int): The ID of the tank for which the maintenance was performed.
            date (str): The date and time of the maintenance in ISO format (e.g., "YYYY-MM-DDTHH:MM:SS").
            m_type (str): The type of maintenance performed (e.g., "Water Change", "Filter Cleaning").
                          Will be stripped of leading/trailing whitespace.
            description (Optional[str]): An optional detailed description of the maintenance.
                                         Stored as `None` if an empty string.
            volume_changed (Optional[float]): Optional percentage of water changed (e.g., 25.0, 50.0).
                                              Stored as `None` if not applicable or 0.
            cost (Optional[float]): Optional cost associated with the maintenance.
                                    Stored as `None` if not applicable or 0.
            notes (Optional[str]): Optional additional notes about the maintenance.
                                   Stored as `None` if an empty string.
            next_due (Optional[str]): Optional calculated next due date for the maintenance
                                      in ISO format (YYYY-MM-DD).
            cycle_id (Optional[int]): Optional ID of the associated recurring maintenance cycle,
                                      linking this log entry to a defined schedule. Defaults to `None`.

        Raises:
            sqlite3.Error: If a database error occurs during insertion (e.g., foreign key violation).
            RuntimeError: If a general operational error occurs in the BaseRepository.
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

    def get_maintenance(self, *, tank_id: int) -> List[MaintenanceLogRecord]: # Updated return type
        """
        Retrieves all maintenance log entries for a specific tank,
        ordered from most recent to oldest.

        Includes the name of the associated cycle (if any) via a JOIN operation.

        Args:
            tank_id (int): The ID of the tank to fetch maintenance records for.
                           This is a keyword-only argument.

        Returns:
            List[MaintenanceLogRecord]: A list of dictionaries, where each dictionary
                                  represents a maintenance log entry. Typical keys
                                  include: `id`, `tank_id`, `cycle_id`, `date`,
                                  `maintenance_type`, `description`, `volume_changed`,
                                  `cost`, `notes`, `next_due`, `is_completed`,
                                  `created_at`, and `cycle_name` (from joined table).
                                  Returns an empty list if no records are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
            RuntimeError: If a general operational error occurs in the BaseRepository.
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
        Deletes a specific maintenance log entry by its unique ID.

        Args:
            record_id (int): The unique identifier of the maintenance record to delete.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_log WHERE id = ?;", (record_id,))
            conn.commit()

    def fetch_maintenance_cycles(self, tank_id: int) -> List[MaintenanceCycleRecord]: # Updated return type
        """
        Retrieves all defined recurring maintenance cycles for a specific tank.

        Args:
            tank_id (int): The ID of the tank to fetch maintenance cycles for.

        Returns:
            List[MaintenanceCycleRecord]: A list of dictionaries, where each dictionary
                                  represents a maintenance cycle. Typical keys
                                  include: `id`, `type` (renamed from `maintenance_type`),
                                  `date` (renamed from `created_at`), `notes`,
                                  `frequency_days`, `is_active`.
                                  Returns an empty list if no cycles are found.

        Raises:
            sqlite3.Error: If a database error occurs during fetching.
            RuntimeError: If a general operational error occurs in the BaseRepository.
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
            tank_id (int): The ID of the tank to which this cycle applies.
            maintenance_type (str): The type of recurring maintenance (e.g., "Weekly Water Change").
                                    Will be stripped of leading/trailing whitespace.
            frequency_days (int): The frequency of the cycle in days (e.g., 7 for weekly).
                                  Must be a positive integer.
            description (Optional[str]): An optional detailed description of the cycle.
                                         Stored as `None` if an empty string.
            notes (Optional[str]): Optional additional notes about the cycle.
                                   Stored as `None` if an empty string.
            is_active (bool): Boolean indicating if the cycle is currently active. Defaults to `True`.

        Raises:
            sqlite3.Error: If a database error occurs during insertion (e.g., check constraint violation
                           for `frequency_days` or foreign key violation).
            RuntimeError: If a general operational error occurs in the BaseRepository.
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
        Deletes a specific maintenance cycle by its unique ID.

        Note: Associated entries in `maintenance_log` will have their `cycle_id`
        set to `NULL` due to the `ON DELETE SET NULL` foreign key constraint
        defined in the database schema.

        Args:
            cycle_id (int): The unique identifier of the maintenance cycle to delete.

        Raises:
            sqlite3.Error: If a database error occurs during deletion.
            RuntimeError: If a general operational error occurs in the BaseRepository.
        """
        with get_connection() as conn:
            conn.execute("DELETE FROM maintenance_cycles WHERE id = ?;", (cycle_id,))
            conn.commit()