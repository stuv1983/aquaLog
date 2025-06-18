# aqualog_db/repositories/custom_range.py

"""
custom_range.py – Custom Safe Range Repository

Manages custom safe parameter ranges on a per-tank basis. This allows users to
override the global default safe ranges for specific aquariums with unique
requirements.
"""

from typing import Optional, Tuple, Dict, List, Any
from ..base import BaseRepository

class CustomRangeRepository(BaseRepository):
    """Handles custom parameter range operations with validation."""
    
    VALID_PARAMETERS = {
        'ph', 'ammonia', 'nitrite', 'nitrate', 
        'kh', 'gh', 'temperature'
    }
    
    def get(self, tank_id: int, parameter: str) -> Optional[Tuple[float, float]]:
        """Get custom range for a tank and parameter."""
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
        """Set or update a custom range and return the saved record."""
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
                    ON CONFLICT(tank_id, parameter)
                    DO UPDATE SET safe_low = excluded.safe_low,
                                  safe_high = excluded.safe_high,
                                  updated_at = datetime('now');
                    """,
                    (tank_id, parameter, low, high)
                )
                # Get the inserted/updated record
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
                    raise ValueError(f"Invalid range values: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def get_all_for_tank(self, tank_id: int) -> Dict[str, Tuple[float, float]]:
        """Get all custom ranges for a tank as {parameter: (low, high)}."""
        self._validate_tank_id(tank_id)
        
        ranges = self._query_all(
            "SELECT parameter, safe_low, safe_high FROM custom_ranges WHERE tank_id = ?;",
            (tank_id,)
        )
        return {r['parameter']: (r['safe_low'], r['safe_high']) for r in ranges}

    def _validate_tank_id(self, tank_id: int):
        """Validate tank ID."""
        if not isinstance(tank_id, int) or tank_id < 1:
            raise ValueError("Invalid tank ID: must be positive integer")

    def _validate_parameter(self, parameter: str):
        """Validate parameter name."""
        if parameter not in self.VALID_PARAMETERS:
            raise ValueError(
                f"Invalid parameter: must be one of {sorted(self.VALID_PARAMETERS)}"
            )

    def _validate_range_values(self, low: float, high: float):
        """Validate range values."""
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            raise ValueError("Range values must be numbers")
        if high <= low:
            raise ValueError("High value must be greater than low value")