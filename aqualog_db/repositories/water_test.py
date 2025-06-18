# aqualog_db/repositories/water_test.py

"""
water_test.py – Water Test Data Repository

Handles all database operations for the `water_tests` table. Includes methods
for saving new water test entries and fetching historical data based on date
ranges and tank IDs.
"""

from datetime import datetime
import pandas as pd
from typing import Dict, Optional, List, Any, Tuple
import sqlite3
from aqualog_db.connection import get_connection  # import the contextmanager
from ..base import BaseRepository

class WaterTestRepository(BaseRepository):
    """Handles all water test-related database operations with validation."""
    
    VALID_CO2_INDICATORS = {"Green", "Blue", "Yellow"}
    VALID_PARAMETERS = {
        "ph": (0, 14),
        "ammonia": (0, 10),
        "nitrite": (0, 5),
        "nitrate": (0, 100),
        "temperature": (0, 40),
        "kh": (0, 30),
        "gh": (0, 30)
    }
    
    def save(self, data: dict, tank_id: int = 1) -> Dict[str, Any]:
        """Save a water test record with validation and return the saved record."""
        self._validate_input(data, tank_id)
        payload = self._prepare_payload(data, tank_id)
        
        # Use get_connection directly to avoid GeneratorContextManager misusage
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(water_tests);")
            valid_columns = {row['name'] for row in cursor.fetchall()}
            
            filtered_payload = {k: v for k, v in payload.items() if k in valid_columns}
            columns = ", ".join(filtered_payload.keys())
            placeholders = ", ".join("?" for _ in filtered_payload)
            
            try:
                cursor.execute(
                    f"INSERT INTO water_tests ({columns}) VALUES ({placeholders});",
                    tuple(filtered_payload.values())
                )
                inserted_id = cursor.lastrowid
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid parameter value: {e}")
                if "FOREIGN KEY" in str(e):
                    raise ValueError("Invalid tank ID")
                raise RuntimeError(f"Database error: {e}")
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {e}")

        # Fetch inserted record
        with get_connection() as conn:
            return self.fetch_one(
                "SELECT * FROM water_tests WHERE id = ?;",
                (inserted_id,)
            )

    def _validate_input(self, data: dict, tank_id: int):
        """Validate all input parameters."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")
        if 'date' in data and not isinstance(data['date'], str):
            raise ValueError("Date must be a string")
        if 'co2_indicator' in data and data['co2_indicator'] not in self.VALID_CO2_INDICATORS:
            raise ValueError(f"CO2 indicator must be one of {self.VALID_CO2_INDICATORS}")

    def _prepare_payload(self, data: dict, tank_id: int) -> dict:
        """Prepare and validate the payload."""
        payload = data.copy()
        payload['tank_id'] = tank_id
        payload.setdefault("date", datetime.now().isoformat(timespec="seconds"))
        
        for field, (min_val, max_val) in self.VALID_PARAMETERS.items():
            if field in payload and payload[field] is not None:
                try:
                    value = float(payload[field])
                    if not (min_val <= value <= max_val):
                        raise ValueError(f"{field} must be between {min_val} and {max_val}")
                    payload[field] = value
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid value for {field} - must be numeric between {min_val} and {max_val}")
        return payload

    def fetch_by_date_range(
        self,
        start: str,
        end: str,
        tank_id: Optional[int] = None
    ) -> pd.DataFrame:
        """Fetch water tests within a date range as a DataFrame."""
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
                return pd.read_sql_query(
                    query, conn, params=params, parse_dates=['date']
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data: {e}") from e

    def get_latest_for_tank(self, tank_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent water test for a specific tank."""
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        return self.fetch_one(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;",
            (tank_id,)
        )

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent water test across all tanks."""
        return self.fetch_one(
            "SELECT * FROM water_tests ORDER BY date DESC LIMIT 1;"
        )

    def get_custom_ranges(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """Get all custom ranges for a tank as {parameter: (low, high)}."""
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        ranges = self._query_all(
            "SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;",
            (tank_id,)
        )
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}
