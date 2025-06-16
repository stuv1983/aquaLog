"""
schema.py – Full database schema with all tables, indexes, triggers, and in-place migrations
"""
import sqlite3
from .base import BaseRepository

class SchemaManager(BaseRepository):
    """Handles database schema creation, in-place migrations, and triggers."""

    # ───────────────────────────────────────────────────────────────────────────
    # Table Definitions
    # ───────────────────────────────────────────────────────────────────────────
    TABLE_SCHEMAS = {
        "tanks": """
            CREATE TABLE IF NOT EXISTS tanks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL CHECK(length(trim(name)) > 0),
                volume_l    REAL    CHECK(volume_l IS NULL OR volume_l >= 0),
                start_date  TEXT,
                notes       TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
        """,

        "water_tests": """
            CREATE TABLE IF NOT EXISTS water_tests (
                id            INTEGER PRIMARY KEY,
                date          TEXT    NOT NULL CHECK(date != ''),
                ph            REAL    CHECK(ph >= 0 AND ph <= 14),
                ammonia       REAL    CHECK(ammonia >= 0 AND ammonia <= 10),
                nitrite       REAL    CHECK(nitrite >= 0 AND nitrite <= 5),
                nitrate       REAL    CHECK(nitrate >= 0 AND nitrate <= 100),
                temperature   REAL    CHECK(temperature >= 0 AND temperature <= 40),
                kh            REAL    DEFAULT 0 CHECK(kh >= 0 AND kh <= 30),
                co2_indicator TEXT    CHECK(co2_indicator IN ('Green', 'Blue', 'Yellow')),
                gh            REAL    DEFAULT 0 CHECK(gh >= 0 AND gh <= 30),
                tank_id       INTEGER NOT NULL,
                notes         TEXT,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """,

        "plants": """
            CREATE TABLE IF NOT EXISTS plants (
                plant_id      INTEGER PRIMARY KEY,
                plant_name    TEXT    NOT NULL CHECK(length(trim(plant_name)) > 0),
                origin        TEXT,
                origin_info   TEXT,
                growth_rate   TEXT,
                growth_info   TEXT,
                height_cm     TEXT,
                height_info   TEXT,
                light_demand  TEXT,
                light_info    TEXT,
                co2_demand    TEXT,
                co2_info      TEXT,
                thumbnail_url TEXT,
                created_at    TEXT    DEFAULT (datetime('now')),
                updated_at    TEXT    DEFAULT (datetime('now'))
            );
        """,

        "owned_plants": """
            CREATE TABLE IF NOT EXISTS owned_plants (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id     INTEGER NOT NULL,
                common_name  TEXT,
                tank_id      INTEGER NOT NULL,
                created_at   TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (plant_id) REFERENCES plants(plant_id) ON DELETE CASCADE,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """,

        "fish": """
            CREATE TABLE IF NOT EXISTS fish (
                fish_id         INTEGER PRIMARY KEY,
                scientific_name TEXT    NOT NULL CHECK(length(trim(scientific_name)) > 0),
                common_name     TEXT,
                image_url       TEXT,
                created_at      TEXT    DEFAULT (datetime('now')),
                updated_at      TEXT    DEFAULT (datetime('now'))
            );
        """,

        "owned_fish": """
            CREATE TABLE IF NOT EXISTS owned_fish (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                fish_id      INTEGER NOT NULL,
                common_name  TEXT,
                tank_id      INTEGER NOT NULL,
                quantity     INTEGER DEFAULT 1,
                created_at   TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (fish_id) REFERENCES fish(fish_id) ON DELETE CASCADE,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """,

        "cycles": """
            CREATE TABLE IF NOT EXISTS cycles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date      TEXT    NOT NULL,
                completed_date  TEXT,
                notes           TEXT,
                created_at      TEXT    DEFAULT (datetime('now')),
                updated_at      TEXT    DEFAULT (datetime('now'))
            );
        """,

        "maintenance_cycles": """
            CREATE TABLE IF NOT EXISTS maintenance_cycles (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tank_id          INTEGER NOT NULL,
                maintenance_type TEXT    NOT NULL CHECK(length(trim(maintenance_type)) > 0),
                frequency_days   INTEGER NOT NULL CHECK(frequency_days > 0),
                description      TEXT,
                notes           TEXT,
                is_active        BOOLEAN DEFAULT 1,
                created_at       TEXT    DEFAULT (datetime('now')),
                updated_at       TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """,

        "maintenance_log": """
            CREATE TABLE IF NOT EXISTS maintenance_log (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tank_id          INTEGER NOT NULL,
                cycle_id         INTEGER,
                date             TEXT    NOT NULL,
                maintenance_type TEXT    NOT NULL CHECK(length(trim(maintenance_type)) > 0),
                description      TEXT,
                volume_changed   REAL    CHECK(volume_changed IS NULL OR volume_changed >= 0),
                cost             REAL    CHECK(cost IS NULL OR cost >= 0),
                notes            TEXT,
                next_due         TEXT,
                is_completed     BOOLEAN DEFAULT 1,
                created_at       TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE,
                FOREIGN KEY (cycle_id) REFERENCES maintenance_cycles(id) ON DELETE SET NULL
            );
        """,

        "email_settings": """
            CREATE TABLE IF NOT EXISTS email_settings (
                user_id        INTEGER PRIMARY KEY DEFAULT 1,
                email          TEXT    CHECK(email IS NULL OR email LIKE '%@%.%'),
                tanks          TEXT,
                include_type   BOOLEAN DEFAULT 1,
                include_date   BOOLEAN DEFAULT 1,
                include_notes  BOOLEAN DEFAULT 0,
                include_cost   BOOLEAN DEFAULT 0,
                include_stats  BOOLEAN DEFAULT 1,
                include_cycle  BOOLEAN DEFAULT 0,
                created_at     TEXT    DEFAULT (datetime('now')),
                updated_at     TEXT    DEFAULT (datetime('now'))
            );
        """,

        "custom_ranges": """
            CREATE TABLE IF NOT EXISTS custom_ranges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tank_id     INTEGER NOT NULL,
                parameter   TEXT    NOT NULL CHECK(parameter IN ('ph','ammonia','nitrite','nitrate','kh','gh','temperature')),
                safe_low    REAL    NOT NULL,
                safe_high   REAL    NOT NULL CHECK(safe_high > safe_low),
                created_at  TEXT    DEFAULT (datetime('now')),
                updated_at  TEXT    DEFAULT (datetime('now')),
                UNIQUE(tank_id, parameter),
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """
    }

    # ───────────────────────────────────────────────────────────────────────────
    # Index Definitions
    # ───────────────────────────────────────────────────────────────────────────
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_water_tests_date ON water_tests(date);",
        "CREATE INDEX IF NOT EXISTS idx_water_tests_tank_id ON water_tests(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_log_tank_id ON maintenance_log(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_cycles_tank_id ON maintenance_cycles(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_log_cycle_id ON maintenance_log(cycle_id);",
        "CREATE INDEX IF NOT EXISTS idx_custom_ranges_tank_id ON custom_ranges(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_owned_plants_tank_id ON owned_plants(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_owned_fish_tank_id ON owned_fish(tank_id);"
    ]

    # ───────────────────────────────────────────────────────────────────────────
    # Trigger Definitions
    # ───────────────────────────────────────────────────────────────────────────
    TRIGGERS = [
        """
        CREATE TRIGGER IF NOT EXISTS update_tank_timestamp
        AFTER UPDATE ON tanks
        FOR EACH ROW
        BEGIN
            UPDATE tanks SET updated_at = datetime('now') WHERE id = OLD.id;
        END;
        """,
        
        """
        CREATE TRIGGER IF NOT EXISTS update_plants_timestamp
        AFTER UPDATE ON plants
        FOR EACH ROW
        BEGIN
            UPDATE plants SET updated_at = datetime('now') WHERE plant_id = OLD.plant_id;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS update_maintenance_cycles_timestamp
        AFTER UPDATE ON maintenance_cycles
        FOR EACH ROW
        BEGIN
            UPDATE maintenance_cycles SET updated_at = datetime('now') WHERE id = OLD.id;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS set_next_maintenance_due
        AFTER INSERT ON maintenance_log
        FOR EACH ROW WHEN NEW.cycle_id IS NOT NULL AND NEW.is_completed = 1
        BEGIN
            UPDATE maintenance_log 
            SET next_due = date(
                NEW.date, 
                '+' || (SELECT frequency_days FROM maintenance_cycles WHERE id = NEW.cycle_id) || ' days'
            )
            WHERE id = NEW.id;
        END;
        """
    ]

    # ───────────────────────────────────────────────────────────────────────────
    # Initialize and Migrate Tables
    # ───────────────────────────────────────────────────────────────────────────
    def init_tables(self) -> None:
        """
        Initialize all tables, perform in-place migrations, create indexes and triggers.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            # 1) Create or update all tables
            for schema_sql in self.TABLE_SCHEMAS.values():
                cursor.execute(schema_sql)

            # 2) In-place migrations: add missing columns
            self._ensure_column(cursor, 'water_tests', 'gh',      "REAL DEFAULT 0 CHECK(gh >= 0 AND gh <= 30)")
            self._ensure_column(cursor, 'water_tests', 'tank_id', "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(cursor, 'water_tests', 'notes',   "TEXT")
            self._ensure_column(cursor, 'maintenance_log', 'cycle_id', "INTEGER")
            self._ensure_column(cursor, 'maintenance_log', 'is_completed', "BOOLEAN DEFAULT 1")

            for tbl in ('maintenance_log', 'custom_ranges', 'owned_plants', 'owned_fish'):
                self._ensure_column(cursor, tbl, 'tank_id', "INTEGER NOT NULL DEFAULT 1")
            
            # Ensure owned_fish has quantity column for older databases
            self._ensure_column(cursor, 'owned_fish', 'quantity', 'INTEGER DEFAULT 1')


            # 3) Create indexes
            for idx_sql in self.INDEXES:
                cursor.execute(idx_sql)

            # 4) Create triggers
            for trg_sql in self.TRIGGERS:
                cursor.execute(trg_sql)

            # 5) Seed default tank
            cursor.execute(
                "INSERT OR IGNORE INTO tanks (id, name) VALUES (1, 'Default Tank');"
            )
            conn.commit()

    def _ensure_column(self, cursor: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
        """
        Add a column to an existing table if it does not already exist.
        """
        cursor.execute(f"PRAGMA table_info({table});")
        existing = {row[1] for row in cursor.fetchall()}
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl};")
