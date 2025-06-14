# aqualog_db/queries.py

import sqlite3
import pandas as pd
from aqualog_db.connection import get_connection
from .repositories.water_test import WaterTestRepository


def fetch_all_tanks() -> pd.DataFrame:
    """
    Return a DataFrame of all tanks in the database.
    """
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM tanks ORDER BY id", conn)
    return df


def fetch_data(start_date: str, end_date: str, tank_id: int) -> pd.DataFrame:
    """
    Return water_tests between start_date and end_date for the given tank_id.
    Dates must be ISO-formatted strings.
    """
    sql = (
        "SELECT * FROM water_tests"
        " WHERE date BETWEEN ? AND ?"
        " AND tank_id = ?"
        " ORDER BY date"
    )
    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=(start_date, end_date, tank_id))
    return df


def get_custom_ranges(tank_id: int) -> dict[str, tuple[float, float]]:
    """
    Fetch custom safe ranges for a given tank. Returns mapping of parameter -> (safe_low, safe_high).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT parameter, safe_low, safe_high "
            "FROM custom_ranges WHERE tank_id = ?",
            (tank_id,)
        )
        rows = cursor.fetchall()
    return {param: (low, high) for param, low, high in rows}


def set_custom_range(
    tank_id: int,
    parameter: str,
    safe_low: float,
    safe_high: float
) -> None:
    """
    Create or update a custom range for a tank and parameter.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO custom_ranges (tank_id, parameter, safe_low, safe_high)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tank_id, parameter)
            DO UPDATE SET safe_low = excluded.safe_low, safe_high = excluded.safe_high
            """,
            (tank_id, parameter, safe_low, safe_high)
        )
        conn.commit()


def get_user_email_settings() -> dict[str, any]:
    """
    Retrieve the current email settings for the default user (user_id = 1).
    Returns a dict of settings fields.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM email_settings WHERE user_id = 1")
        row = cursor.fetchone()
    if not row:
        return {}
    return dict(row)


def save_user_email_settings(
    email: str | None,
    tanks: str | None,
    include_type: bool,
    include_date: bool,
    include_notes: bool,
    include_cost: bool,
    include_stats: bool,
    include_cycle: bool,
) -> None:
    """
    Insert or update the email_settings record for the default user (user_id = 1).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO email_settings (
                user_id, email, tanks,
                include_type, include_date, include_notes,
                include_cost, include_stats, include_cycle
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email = excluded.email,
                tanks = excluded.tanks,
                include_type = excluded.include_type,
                include_date = excluded.include_date,
                include_notes = excluded.include_notes,
                include_cost = excluded.include_cost,
                include_stats = excluded.include_stats,
                include_cycle = excluded.include_cycle
            """,
            (
                email, tanks,
                int(include_type), int(include_date), int(include_notes),
                int(include_cost), int(include_stats), int(include_cycle)
            ),
        )
        conn.commit()


def add_tank(
    name: str,
    volume_l: float | None = None,
    start_date: str | None = None,
    notes: str | None = None
) -> int:
    """
    Create a new tank and return its ID.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tanks (name, volume_l, start_date, notes)
            VALUES (?, ?, ?, ?);
            """,
            (name, volume_l, start_date, notes),
        )
        conn.commit()
        return cursor.lastrowid


def remove_tank(tank_id: int) -> None:
    """
    Delete a tank (and, via ON DELETE CASCADE, all its related records).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tanks WHERE id = ?", (tank_id,))
        conn.commit()


def save_water_test(data: dict, tank_id: int = 1) -> dict:
    """
    Save a water test record and return the saved record.
    """
    repo = WaterTestRepository()
    return repo.save(data, tank_id)
