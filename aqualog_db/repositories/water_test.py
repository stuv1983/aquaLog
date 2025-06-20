# aqualog_db/repositories/water_test.py

"""
water_test.py – Water Test Data Repository

Handles all database operations for the `water_tests` table. Includes methods
for saving new water test entries and fetching historical data based on date
ranges and tank IDs. It also incorporates validation logic for water parameters.
"""

from datetime import datetime
import pandas as pd
from typing import Dict, Optional, List, Any, Tuple
import sqlite3
from aqualog_db.connection import get_connection
from ..base import BaseRepository

class WaterTestRepository(BaseRepository):
    """
    Manages database interactions for `water_tests` records.

    Provides methods to save, retrieve, and validate water quality test data,
    associated with specific tanks.
    """
    
    # Define valid CO2 indicator states for validation.
    VALID_CO2_INDICATORS = {"Green", "Blue", "Yellow"}

    # Define valid ranges for numeric water parameters for validation.
    # Format: "parameter_name": (min_allowed_value, max_allowed_value)
    VALID_PARAMETERS = {
        "ph": (0, 14),
        "ammonia": (0, 100), # Ammonia concentration in ppm
        "nitrite": (0, 100), # Nitrite concentration in ppm
        "nitrate": (0, 100), # Nitrate concentration in ppm
        "temperature": (0, 40), # Temperature in Celsius
        "kh": (0, 30), # Carbonate Hardness in dKH
        "gh": (0, 30) # General Hardness in dGH
    }
    
    def save(self, data: dict, tank_id: int = 1) -> Dict[str, Any]:
        """
        Saves a new water test record to the database after validation.

        Args:
            data: A dictionary containing the water test parameters. Expected keys
                  include 'date', 'ph', 'ammonia', 'nitrite', 'nitrate',
                  'temperature', 'kh', 'co2_indicator', 'gh', 'notes'.
            tank_id: The ID of the tank for which the test was performed. Defaults to 1.

        Returns:
            Dict[str, Any]: A dictionary representing the newly saved water test record.

        Raises:
            ValueError: If any input data fails validation (e.g., out-of-range values,
                        invalid types, invalid CO2 indicator).
            RuntimeError: If a database error occurs during insertion.
        """
        self._validate_input(data, tank_id) # Validate general input structure and types
        payload = self._prepare_payload(data, tank_id) # Prepare data and validate parameter ranges
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(water_tests);")
            # Get valid column names from the database schema to filter payload
            valid_columns = {row['name'] for row in cursor.fetchall()}
            
            # Filter the payload to include only columns present in the table
            filtered_payload = {k: v for k, v in payload.items() if k in valid_columns}
            
            columns = ", ".join(filtered_payload.keys())
            placeholders = ", ".join("?" for _ in filtered_payload)
            
            try:
                cursor.execute(
                    f"INSERT INTO water_tests ({columns}) VALUES ({placeholders});",
                    tuple(filtered_payload.values())
                )
                inserted_id = cursor.lastrowid # Get the ID of the newly inserted row
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    # Catch specific SQLite CHECK constraint violations
                    raise ValueError(f"Invalid parameter value: {e}")
                if "FOREIGN KEY" in str(e):
                    # Catch foreign key constraint violations (e.g., non-existent tank_id)
                    raise ValueError("Invalid tank ID: tank does not exist.")
                raise RuntimeError(f"Database error: {e}")
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {e}")

        # Fetch the complete inserted record to ensure consistency and return
        with get_connection() as conn:
            return self.fetch_one(
                "SELECT * FROM water_tests WHERE id = ?;",
                (inserted_id,)
            )

    def _validate_input(self, data: dict, tank_id: int):
        """
        Performs initial validation on the raw input data and tank ID.

        Args:
            data: The raw dictionary of water test parameters.
            tank_id: The ID of the tank.

        Raises:
            ValueError: If data is not a dictionary, tank_id is invalid,
                        date is not a string, or co2_indicator is invalid.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")
        if 'date' in data and not isinstance(data['date'], str):
            raise ValueError("Date must be a string (ISO format expected).")
        if 'co2_indicator' in data and data['co2_indicator'] not in self.VALID_CO2_INDICATORS:
            raise ValueError(f"CO2 indicator must be one of {self.VALID_CO2_INDICATORS}")

    def _prepare_payload(self, data: dict, tank_id: int) -> dict:
        """
        Prepares the payload for database insertion, including default values
        and numerical parameter validation.

        Args:
            data: The raw dictionary of water test parameters.
            tank_id: The ID of the tank.

        Returns:
            dict: A dictionary containing prepared and validated payload for the database.

        Raises:
            ValueError: If any numeric parameter is outside its `VALID_PARAMETERS` range
                        or cannot be converted to a float.
        """
        payload = data.copy()
        payload['tank_id'] = tank_id
        # Set current time as default if 'date' is not provided
        payload.setdefault("date", datetime.now().isoformat(timespec="seconds"))
        
        # Validate and coerce numeric parameters to float
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
        """
        Fetches water test records within a specified date range for a given tank.

        Args:
            start: The start date of the range (ISO formatted string, e.g., "YYYY-MM-DD").
            end: The end date of the range (ISO formatted string).
            tank_id: Optional. The ID of the tank to filter by. If None, fetches for all tanks.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the matching water test records,
                          with the 'date' column parsed as datetime objects.
                          Returns an empty DataFrame if no data is found.

        Raises:
            ValueError: If start/end dates are not strings or tank_id is invalid.
            RuntimeError: If a database error occurs during fetching.
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
        
        query += " ORDER BY date ASC" # Order results chronologically
        
        try:
            with get_connection() as conn:
                # Use pd.read_sql_query for direct DataFrame conversion and date parsing
                return pd.read_sql_query(
                    query, conn, params=params, parse_dates=['date']
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data: {e}") from e

    def get_latest_for_tank(self, tank_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent water test record for a specific tank.

        Args:
            tank_id: The ID of the tank to retrieve the latest test for.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the latest test record,
                                      or None if no tests are found for the tank.

        Raises:
            ValueError: If `tank_id` is invalid.
            RuntimeError: If a database error occurs.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        return self.fetch_one(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;",
            (tank_id,)
        )

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the single most recent water test record across all tanks.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the latest test record,
                                      or None if no tests are found in the database.

        Raises:
            RuntimeError: If a database error occurs.
        """
        return self.fetch_one(
            "SELECT * FROM water_tests ORDER BY date DESC LIMIT 1;"
        )

    def get_custom_ranges(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """
        Retrieves all custom safe ranges defined for a specific tank.

        This method queries the `custom_ranges` table.

        Args:
            tank_id: The ID of the tank to retrieve custom ranges for.

        Returns:
            Dict[str, Tuple[float, float]]: A dictionary where keys are parameter names
                                            and values are tuples (safe_low, safe_high).

        Raises:
            ValueError: If `tank_id` is invalid.
            RuntimeError: If a database error occurs.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        # Queries the custom_ranges table for the given tank_id
        ranges = self.fetch_all( # Corrected from self._query_all to self.fetch_all
            "SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;",
            (tank_id,)
        )
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}