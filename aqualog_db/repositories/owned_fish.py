# aqualog_db/repositories/owned_fish.py

"""
owned_fish.py – Owned Fish Data Repository

Handles all database operations for the `owned_fish` table.
"""
import pandas as pd
from ..base import BaseRepository
from ..connection import get_connection

class OwnedFishRepository(BaseRepository):
    """Handles operations for the owned_fish table."""

    def add_to_tank(self, fish_id: int, tank_id: int) -> None:
        """Add a fish to a specific tank's inventory."""
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO owned_fish (fish_id, tank_id, quantity)
                VALUES (?, ?, 1) ON CONFLICT(fish_id, tank_id) DO NOTHING
            """, (fish_id, tank_id))
            conn.commit()

    def fetch_for_tank_with_details(self, tank_id: int) -> pd.DataFrame:
        """Fetch all fish for a given tank, with details from the master fish table."""
        with get_connection() as conn:
            return pd.read_sql_query("""
                SELECT
                    o.id as owned_fish_id, o.quantity, p.*
                FROM owned_fish o
                JOIN fish p ON o.fish_id = p.fish_id
                WHERE o.tank_id = ?
                ORDER BY p.species_name COLLATE NOCASE
            """, conn, params=(tank_id,))

    def remove_from_tank(self, owned_fish_id: int) -> None:
        """Remove a fish from a tank's inventory by its owned_fish ID."""
        with get_connection() as conn:
            conn.execute("DELETE FROM owned_fish WHERE id = ?", (owned_fish_id,))
            conn.commit()