from aqualog_db.repositories import CustomRangeRepository

def ensure_custom_ranges_schema() -> None:
    """Ensures the custom_ranges table exists in the database."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS custom_ranges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tank_id INTEGER NOT NULL,
                parameter TEXT NOT NULL,
                safe_low REAL NOT NULL,
                safe_high REAL NOT NULL,
                UNIQUE(tank_id, parameter)
            );
        """)
        conn.commit()

def ensure_water_tests_schema() -> None:
    """Ensures the water_tests table exists by delegating to db.init_tables."""
    from db import init_tables
    init_tables()