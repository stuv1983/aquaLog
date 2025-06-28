# aqualog_db/repositories/water_test.py

"""
water_test.py – Water Test Data Repository

Handles all database operations for the `water_tests` table. Includes methods
for saving new water test entries and fetching historical data based on date
ranges and tank IDs. It also incorporates validation logic for water parameters.
"""

from __future__ import annotations
from datetime import datetime
import pandas as pd
from typing import Dict, Optional, List, Any, Tuple, TypedDict
import sqlite3
from aqualog_db.connection import get_connection
from ..base import BaseRepository

# Define a TypedDict for the structure of a water test record.
class WaterTestRecord(TypedDict, total=False):
    """Represents a single row/record from the `water_tests` table."""
    id: int
    date: str
    ph: Optional[float]
    ammonia: Optional[float]
    nitrite: Optional[float]
    nitrate: Optional[float]
    temperature: Optional[float]
    kh: Optional[float]
    co2_indicator: Optional[str]
    gh: Optional[float]
    tank_id: int
    notes: Optional[str]

class WaterTestRepository(BaseRepository):
    """
    Manages database interactions for `water_tests` records.

    Provides methods to save, retrieve, and validate water quality test data,
    associated with specific tanks.
    """

    VALID_CO2_INDICATORS: set[str] = {"Green", "Blue", "Yellow"}
    VALID_PARAMETERS: dict[str, Tuple[int, int]] = {
        "ph": (0, 14),
        "ammonia": (0, 100),
        "nitrite": (0, 100),
        "nitrate": (0, 100),
        "temperature": (0, 40),
        "kh": (0, 30),
        "gh": (0, 30)
    }

    def save(self, data: WaterTestRecord, tank_id: int = 1) -> WaterTestRecord:
        """
        Saves a new water test record to the database after validation.
        """
        self._validate_input(dict(data), tank_id)
        payload: WaterTestRecord = self._prepare_payload(data, tank_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(water_tests);")
            valid_columns = {row['name'] for row in cursor.fetchall()}
            filtered_payload = {k: v for k, v in payload.items() if k in valid_columns}
            
            # Use parameterized query to prevent SQL injection
            columns = ", ".join(filtered_payload.keys())
            placeholders = ", ".join("?" for _ in filtered_payload)
            sql = f"INSERT INTO water_tests ({columns}) VALUES ({placeholders})"
            
            try:
                cursor.execute(sql, tuple(filtered_payload.values()))
                inserted_id = cursor.lastrowid
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid parameter value: {e}")
                if "FOREIGN KEY" in str(e):
                    raise ValueError("Invalid tank ID: tank does not exist.")
                raise RuntimeError(f"Database error: {e}")
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {e}")

        with get_connection() as conn:
            result = self.fetch_one("SELECT * FROM water_tests WHERE id = ?;", (inserted_id,))
            return WaterTestRecord(result) if result else None

    def _validate_input(self, data: dict, tank_id: int) -> None:
        """
        Performs initial, high-level validation on the raw input data dictionary
        and the tank ID.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")
        if 'date' in data and not isinstance(data['date'], str):
            raise ValueError("Date must be a string (ISO format expected).")
        if 'co2_indicator' in data and data['co2_indicator'] not in self.VALID_CO2_INDICATORS:
            raise ValueError(f"CO2 indicator must be one of {self.VALID_CO2_INDICATORS}")

    def _prepare_payload(self, data: WaterTestRecord, tank_id: int) -> WaterTestRecord:
        """
        Prepares the raw input data into a standardized payload dictionary
        suitable for database insertion.
        """
        payload = data.copy()
        payload['tank_id'] = tank_id
        payload.setdefault("date", datetime.now().isoformat(timespec="seconds"))
        
        for field, (min_val, max_val) in self.VALID_PARAMETERS.items():
            if field in payload:
                raw_value = payload[field]
                if raw_value is None or raw_value == '':
                    payload[field] = None
                    continue
                
                try:
                    value = float(raw_value)
                    if not (min_val <= value <= max_val):
                        raise ValueError(f"{field} ({value}) is outside acceptable range ({min_val} to {max_val}).")
                    payload[field] = value
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid value for {field} ('{raw_value}') - must be a number between {min_val} and {max_val}.")
            else:
                payload.setdefault(field, None)
                
        if 'notes' in payload and (payload['notes'] is None or payload['notes'].strip() == ''):
            payload['notes'] = None
        elif 'notes' in payload:
            payload['notes'] = payload['notes'].strip()

        return payload

    def fetch_by_date_range(self, start: str, end: str, tank_id: Optional[int] = None) -> pd.DataFrame:
        """
        Fetches water test records within a specified date range for a given tank.
        """
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("Start and end dates must be strings")
        
        query = """
            SELECT id, date, ph, ammonia, nitrite, nitrate, temperature,
                   kh, co2_indicator, gh, tank_id, notes
            FROM water_tests
            WHERE date BETWEEN ? AND ?
        """
        params: List[Any] = [start, end]
        
        if tank_id is not None:
            if not isinstance(tank_id, int) or tank_id < 1:
                raise ValueError("Invalid tank ID")
            query += " AND tank_id = ?"
            params.append(tank_id)
        
        query += " ORDER BY date ASC"
        
        try:
            with get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data: {e}") from e

    def get_latest_for_tank(self, tank_id: int) -> Optional[WaterTestRecord]:
        """
        Retrieves the most recent water test record for a specific tank.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        result = self.fetch_one("SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;", (tank_id,))
        return WaterTestRecord(result) if result else None

    def get_latest(self) -> Optional[WaterTestRecord]:
        """
        Retrieves the single most recent water test record across all tanks.
        """
        result = self.fetch_one("SELECT * FROM water_tests ORDER BY date DESC LIMIT 1;")
        return WaterTestRecord(result) if result else None

    def get_custom_ranges(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """
        Retrieves all custom safe ranges defined for a specific tank.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        ranges = self.fetch_all("SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;", (tank_id,))
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}