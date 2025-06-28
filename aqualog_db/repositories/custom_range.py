# aqualog_db/repositories/custom_range.py

"""
custom_range.py – Custom Safe Range Repository

Manages custom safe parameter ranges on a per-tank basis. This allows users to
override the global default safe ranges for specific aquariums with unique
requirements. It provides CRUD operations for these custom ranges.
"""

from __future__ import annotations # Added for type hinting consistency

from typing import Optional, Tuple, Dict, List, Any
from ..base import BaseRepository
import sqlite3 # Imported for type hinting sqlite3.Error and IntegrityError

class CustomRangeRepository(BaseRepository):
    """
    Handles database operations for custom parameter ranges configured by the user
    for individual tanks.

    Provides methods to retrieve, set, and validate custom safe ranges for
    various water parameters.
    """
    
    # Define a set of valid water parameters for which custom safe ranges can be set.
    # This ensures consistency and prevents setting ranges for unrecognized parameters.
    VALID_PARAMETERS: set[str] = {
        'ph', 'ammonia', 'nitrite', 'nitrate', 
        'kh', 'gh', 'temperature'
    }
    
    def get(self, tank_id: int, parameter: str) -> Optional[Tuple[float, float]]:
        """
        Retrieves the custom safe range (low and high values) for a specific
        tank and parameter from the `custom_ranges` table.

        Args:
            tank_id (int): The unique identifier of the tank.
            parameter (str): The name of the parameter (e.g., "ph", "ammonia").

        Returns:
            Optional[Tuple[float, float]]: A tuple `(safe_low, safe_high)` if a
                                           custom range is found for the given
                                           tank and parameter, otherwise `None`.

        Raises:
            ValueError: If `tank_id` is not a positive integer or if `parameter`
                        is not one of the `VALID_PARAMETERS`.
            RuntimeError: If a database error occurs during the fetch operation.
        """
        self._validate_tank_id(tank_id)
        self._validate_parameter(parameter)
        
        result = self.fetch_one(
            "SELECT safe_low, safe_high FROM custom_ranges WHERE tank_id = ? AND parameter = ?;",
            (tank_id, parameter)
        )
        return (result['safe_low'], result['safe_high']) if result else None

    def set(
        self,
        tank_id: int,
        parameter: str,
        low: float,
        high: float
    ) -> Dict[str, Any]:
        """
        Sets or updates a custom safe range for a specific tank and parameter.
        If a range for the given `tank_id` and `parameter` already exists, it
        will be updated (`UPSERT`). Otherwise, a new record is inserted.

        Args:
            tank_id (int): The unique identifier of the tank.
            parameter (str): The name of the parameter.
            low (float): The new safe low value for the parameter.
            high (float): The new safe high value for the parameter.

        Returns:
            Dict[str, Any]: A dictionary representing the complete inserted or
                            updated custom range record.

        Raises:
            ValueError: If input validation fails (e.g., `tank_id` is invalid,
                        `parameter` is not valid, `low` or `high` are not numeric,
                        or `high` is not strictly greater than `low`).
            RuntimeError: If a database error occurs during the operation.
        """
        self._validate_tank_id(tank_id)
        self._validate_parameter(parameter)
        self._validate_range_values(low, high)
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO custom_ranges (tank_id, parameter, safe_low, safe_high)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(tank_id, parameter) -- If a record with this tank_id and parameter exists
                    DO UPDATE SET safe_low = excluded.safe_low, -- Update its safe_low
                                  safe_high = excluded.safe_high, -- Update its safe_high
                                  updated_at = datetime('now'); -- Update timestamp
                    """,
                    (tank_id, parameter, low, high)
                )
                # Fetch the inserted/updated record to confirm and return its full details.
                saved_range = self.fetch_one(
                    """
                    SELECT * FROM custom_ranges 
                    WHERE tank_id = ? AND parameter = ?;
                    """,
                    (tank_id, parameter)
                )
                conn.commit()
                return saved_range
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    # Catch specific SQLite CHECK constraint violations (e.g., high <= low)
                    raise ValueError(f"Invalid range values: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def get_all_for_tank(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """
        Retrieves all custom safe ranges that have been defined for a specific tank.

        Args:
            tank_id (int): The unique identifier of the tank.

        Returns:
            Dict[str, Tuple[float, float]]: A dictionary where keys are parameter names
                                            (str) and values are tuples `(safe_low, safe_high)`
                                            for that parameter. Returns an empty dictionary
                                            if no custom ranges are found for the tank.

        Raises:
            ValueError: If `tank_id` is not a positive integer.
            RuntimeError: If a database error occurs during the fetch operation.
        """
        self._validate_tank_id(tank_id)
        
        ranges = self.fetch_all(
            "SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;",
            (tank_id,)
        )
        # Convert list of dicts to a single dictionary {parameter: (low, high)}
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}

    def _validate_tank_id(self, tank_id: int) -> None:
        """
        Validates if the provided `tank_id` is a valid positive integer.

        Args:
            tank_id (int): The tank ID to validate.

        Raises:
            ValueError: If `tank_id` is not an integer or is not positive (i.e., less than 1).
        """
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be a positive integer")

    def _validate_parameter(self, parameter: str) -> None:
        """
        Validates if the provided `parameter` name is one of the recognized
        and allowed parameters for which custom ranges can be set.

        Args:
            parameter (str): The parameter name to validate.

        Raises:
            ValueError: If `parameter` is not found within the `VALID_PARAMETERS` set.
        """
        if parameter not in self.VALID_PARAMETERS:
            raise ValueError(
                f"Invalid parameter: must be one of {sorted(list(self.VALID_PARAMETERS))}"
            )

    def _validate_range_values(self, low: float, high: float) -> None:
        """
        Validates if the `low` and `high` range values are valid numbers
        and if `high` is strictly greater than `low`.

        Args:
            low (float): The low value of the range.
            high (float): The high value of the range.

        Raises:
            ValueError: If either `low` or `high` are not numeric types (int or float),
                        or if `high` is not strictly greater than `low`.
        """
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            raise ValueError("Range values must be numbers")
        if high <= low:
            raise ValueError("High value must be greater than low value")