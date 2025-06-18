# aqualog_db/repositories/owned_plant.py
import pandas as pd
from ..base import BaseRepository
from ..connection import get_connection

class OwnedPlantRepository(BaseRepository):
    """Handles operations for the owned_plants table."""

    def add_to_tank(self, plant_id: int, tank_id: int, common_name: str) -> None:
        """Add a plant to a specific tank's inventory."""
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO owned_plants (plant_id, common_name, tank_id)
                VALUES (?, ?, ?) ON CONFLICT(plant_id, tank_id) DO NOTHING
            """, (plant_id, common_name, tank_id))
            conn.commit()

    def fetch_for_tank(self, tank_id: int) -> pd.DataFrame:
        """Fetch all plants for a given tank, with details from the master plants table."""
        with get_connection() as conn:
            return pd.read_sql_query("""
                SELECT
                    p.*,
                    COALESCE(NULLIF(o.common_name, ''), p.plant_name) AS display_name
                FROM owned_plants o
                JOIN plants p ON o.plant_id = p.plant_id
                WHERE o.tank_id = ?
                ORDER BY display_name COLLATE NOCASE
            """, conn, params=(tank_id,))

    def remove_from_tank(self, plant_id: int, tank_id: int) -> None:
        """Remove a plant from a tank's inventory."""
        with get_connection() as conn:
            conn.execute("DELETE FROM owned_plants WHERE plant_id = ? AND tank_id = ?", (plant_id, tank_id))
            conn.commit()