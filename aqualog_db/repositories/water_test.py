# aqualog_db/repositories/water_test.py

"""
water_test.py – Water Test Data Repository

Handles all database operations for the `water_tests` table. Includes methods
for saving new water test entries and fetching historical data based on date
ranges and tank IDs. It also incorporates validation logic for water parameters.
"""

from __future__ import annotations # Added for type hinting consistency

from datetime import datetime
import pandas as pd
from typing import Dict, Optional, List, Any, Tuple, TypedDict # Added TypedDict
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
    
    # Define a set of valid CO2 indicator states (colors) for input validation.
    VALID_CO2_INDICATORS: set[str] = {"Green", "Blue", "Yellow"}

    # Define valid numerical ranges for water parameters for input validation.
    # Format: "parameter_name": (min_allowed_value, max_allowed_value)
    VALID_PARAMETERS: dict[str, Tuple[int, int]] = {
        "ph": (0, 14),
        "ammonia": (0, 100), # Ammonia concentration in ppm
        "nitrite": (0, 100), # Nitrite concentration in ppm
        "nitrate": (0, 100), # Nitrate concentration in ppm
        "temperature": (0, 40), # Temperature in Celsius
        "kh": (0, 30), # Carbonate Hardness in dKH
        "gh": (0, 30) # General Hardness in dGH
    }
    
    def save(self, data: WaterTestRecord, tank_id: int = 1) -> WaterTestRecord: # Updated data param and return type
        """
        Saves a new water test record to the database after validation.

        Args:
            data (WaterTestRecord): A dictionary containing the water test parameters.
                         Expected keys and their types are:
                         - 'date' (str): ISO formatted datetime of the test.
                         - 'ph' (float): pH value.
                         - 'ammonia' (float): Ammonia concentration in ppm.
                         - 'nitrite' (float): Nitrite concentration in ppm.
                         - 'nitrate' (float): Nitrate concentration in ppm.
                         - 'temperature' (float): Temperature in Celsius.
                         - 'kh' (float): Carbonate Hardness in dKH.
                         - 'co2_indicator' (str): CO2 drop checker reading ('Green', 'Blue', 'Yellow').
                         - 'gh' (float): General Hardness in dGH.
                         - 'notes' (str, optional): Additional notes.
            tank_id (int): The ID of the tank for which the test was performed. Defaults to 1.

        Returns:
            WaterTestRecord: A dictionary representing the newly saved water test record.
                            Includes all parameters and automatically generated `id`, `tank_id`.

        Raises:
            ValueError: If any input data fails validation (e.g., data is not a dict,
                        invalid tank_id, `date` is not a string, `co2_indicator` is invalid,
                        or any numeric parameter is out of its acceptable range or type).
            RuntimeError: If a database error occurs during insertion (e.g., `sqlite3.Error`),
                          or a foreign key constraint violation (invalid `tank_id`).
        """
        # data is already WaterTestRecord, but _validate_input and _prepare_payload
        # might still expect dict for internal handling, or could be refactored to take TypedDict.
        # For now, pass as dict.
        self._validate_input(dict(data), tank_id) # Validate general input structure and types
        payload: WaterTestRecord = self._prepare_payload(data, tank_id) # Prepare data and validate parameter ranges
        
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
                    # Catch specific SQLite CHECK constraint violations (e.g., parameter value out of SQL schema range)
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
            result = self.fetch_one(
                "SELECT * FROM water_tests WHERE id = ?;",
                (inserted_id,)
            )
            return WaterTestRecord(result) if result else None # Ensure it's a WaterTestRecord

    def _validate_input(self, data: dict, tank_id: int) -> None: # Keep as dict to allow initial flexible input
        """
        Performs initial, high-level validation on the raw input data dictionary
        and the tank ID.

        Args:
            data (dict): The raw dictionary of water test parameters provided for saving.
            tank_id (int): The ID of the tank associated with the water test.

        Raises:
            ValueError: If `data` is not a dictionary, `tank_id` is invalid (not positive int),
                        `date` is provided but not a string, or `co2_indicator` is provided
                        but not one of the `VALID_CO2_INDICATORS`.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")
        if 'date' in data and not isinstance(data['date'], str):
            raise ValueError("Date must be a string (ISO format expected).")
        if 'co2_indicator' in data and data['co2_indicator'] not in self.VALID_CO2_INDICATORS:
            raise ValueError(f"CO2 indicator must be one of {self.VALID_CO2_INDICATORS}")

    def _prepare_payload(self, data: WaterTestRecord, tank_id: int) -> WaterTestRecord: # Updated data param and return type
        """
        Prepares the raw input data into a standardized payload dictionary
        suitable for database insertion. This includes setting default values,
        stripping whitespace from string fields, and validating/coercing numeric
        parameters to float while checking against `VALID_PARAMETERS` ranges.

        Args:
            data (WaterTestRecord): The raw dictionary of water test parameters.
            tank_id (int): The ID of the tank associated with the water test.

        Returns:
            WaterTestRecord: A dictionary containing the prepared and validated payload
                  for database insertion.

        Raises:
            ValueError: If any numeric parameter in `data` is outside its
                        `VALID_PARAMETERS` range or cannot be converted to a float.
        """
        payload = data.copy()
        payload['tank_id'] = tank_id
        # Set current time as default if 'date' is not provided
        payload.setdefault("date", datetime.now().isoformat(timespec="seconds"))
        
        # Validate and coerce numeric parameters to float
        for field, (min_val, max_val) in self.VALID_PARAMETERS.items():
            if field in payload: # Only process if the field exists in the payload
                raw_value = payload[field]
                if raw_value is None or raw_value == '': # Treat empty string as None for numeric fields
                    payload[field] = None
                    continue # Skip range validation for None values
                
                try:
                    value = float(raw_value)
                    if not (min_val <= value <= max_val):
                        raise ValueError(f"{field} ({value}) is outside acceptable range ({min_val} to {max_val}).")
                    payload[field] = value
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid value for {field} ('{raw_value}') - must be a number between {min_val} and {max_val}.")
            else:
                # If a numeric field is missing from the payload, ensure it's set to None for consistency
                payload.setdefault(field, None)
                
        # Ensure 'notes' is handled gracefully if not provided or empty string
        if 'notes' in payload and (payload['notes'] is None or payload['notes'].strip() == ''):
            payload['notes'] = None
        elif 'notes' in payload:
            payload['notes'] = payload['notes'].strip() # Strip notes if present

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
            start (str): The start date of the range (ISO formatted string, e.g., "YYYY-MM-DD").
                         This includes full datetime, typically "YYYY-MM-DDTHH:MM:SS".
            end (str): The end date of the range (ISO formatted string).
                       This includes full datetime, typically "YYYY-MM-DDTHH:MM:SS".
            tank_id (Optional[int]): The ID of the tank to filter by. If `None`,
                                     fetches records for all tanks. Defaults to `None`.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the matching water test records,
                          with the 'date' column parsed as datetime objects.
                          Columns typically include: `id`, `date`, `ph`, `ammonia`,
                          `nitrite`, `nitrate`, `temperature`, `kh`, `co2_indicator`,
                          `gh`, `tank_id`, `notes`.
                          Returns an empty DataFrame if no data is found for the given criteria.

        Raises:
            ValueError: If `start` or `end` dates are not strings, or if `tank_id` is
                        provided but is not a positive integer.
            RuntimeError: If a database error occurs during fetching (e.g., `sqlite3.Error`),
                          or a generic failure during data retrieval.
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

    def get_latest_for_tank(self, tank_id: int) -> Optional[WaterTestRecord]: # Updated return type
        """
        Retrieves the most recent water test record for a specific tank.

        Args:
            tank_id (int): The ID of the tank to retrieve the latest test for.

        Returns:
            Optional[WaterTestRecord]: A dictionary representing the latest test record.
                                      Includes all columns from the `water_tests` table.
                                      Returns `None` if no tests are found for the tank.

        Raises:
            ValueError: If `tank_id` is invalid (not a positive integer).
            RuntimeError: If a database error occurs during fetching.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        result = self.fetch_one(
            "SELECT * FROM water_tests WHERE tank_id = ? ORDER BY date DESC LIMIT 1;",
            (tank_id,)
        )
        return WaterTestRecord(result) if result else None # Ensure it's WaterTestRecord

    def get_latest(self) -> Optional[WaterTestRecord]: # Updated return type
        """
        Retrieves the single most recent water test record across all tanks in the database.

        Returns:
            Optional[WaterTestRecord]: A dictionary representing the latest test record.
                                      Includes all columns from the `water_tests` table.
                                      Returns `None` if no tests are found in the database.

        Raises:
            RuntimeError: If a database error occurs during fetching.
        """
        result = self.fetch_one(
            "SELECT * FROM water_tests ORDER BY date DESC LIMIT 1;"
        )
        return WaterTestRecord(result) if result else None # Ensure it's WaterTestRecord

    def get_custom_ranges(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """
        Retrieves all custom safe ranges defined for a specific tank by querying
        the `custom_ranges` table.

        Args:
            tank_id (int): The ID of the tank to retrieve custom ranges for.

        Returns:
            Dict[str, Tuple[float, float]]: A dictionary where keys are parameter names
                                            (str) and values are tuples `(safe_low, safe_high)`.
                                            Returns an empty dictionary if no custom ranges
                                            are found for the tank.

        Raises:
            ValueError: If `tank_id` is invalid (not a positive integer).
            RuntimeError: If a database error occurs during fetching.
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID")
        # Queries the custom_ranges table for the given tank_id
        ranges = self.fetch_all( # Corrected from self._query_all to self.fetch_all
            "SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;",
            (tank_id,)
        )
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}