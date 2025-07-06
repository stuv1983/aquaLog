# aqualog_db/schema.py

"""
schema.py – Authoritative Database Schema

Defines the complete database structure for AquaLog. Contains all `CREATE TABLE`
statements, as well as definitions for indexes and triggers that enforce data
integrity and automate timestamp updates. This module is responsible for
initializing and migrating the database schema.
"""

from __future__ import annotations
import sqlite3
from .base import BaseRepository

class SchemaManager(BaseRepository):
    """
    Manages the AquaLog database schema, including table creation,
    index definition, and trigger setup.

    This class provides a centralized source of truth for the database structure
    and handles its initialization or updates based on the defined schemas.
    """
    TABLE_SCHEMAS = {
        "tanks": """
            CREATE TABLE IF NOT EXISTS tanks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL CHECK(length(trim(name)) > 0),
                volume_l    REAL    CHECK(volume_l IS NULL OR volume_l >= 0),
                start_date  TEXT,
                notes       TEXT,
                has_co2     BOOLEAN DEFAULT 1,
                co2_on_hour INTEGER CHECK(co2_on_hour >= 0 AND co2_on_hour <= 23),
                co2_off_hour INTEGER CHECK(co2_off_hour >= 0 AND co2_off_hour <= 23),
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
        """,
        "water_tests": """
            CREATE TABLE IF NOT EXISTS water_tests (
                id            INTEGER PRIMARY KEY,
                date          TEXT    NOT NULL CHECK(date != ''),
                ph            REAL    CHECK(ph >= 0 AND ph <= 14),
                ammonia       REAL    CHECK(ammonia >= 0 AND ammonia <= 100),
                nitrite       REAL    CHECK(nitrite >= 0 AND nitrite <= 100),
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
                plant_id     INTEGER NOT NULL,
                tank_id      INTEGER NOT NULL,
                common_name  TEXT,
                quantity     INTEGER DEFAULT 1,
                created_at   TEXT    DEFAULT (datetime('now')),
                PRIMARY KEY (plant_id, tank_id),
                FOREIGN KEY (plant_id) REFERENCES plants(plant_id) ON DELETE CASCADE,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """,
        "fish": """
            CREATE TABLE IF NOT EXISTS fish (
                fish_id         INTEGER PRIMARY KEY,
                species_name    TEXT    NOT NULL,
                common_name     TEXT,
                origin          TEXT,
                phmin           REAL,
                phmax           REAL,
                temperature_min REAL,
                temperature_max REAL,
                tank_size_liter REAL,
                image_url       TEXT,
                swim            INTEGER
            );
        """,
        "owned_fish": """
            CREATE TABLE IF NOT EXISTS owned_fish (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                fish_id      INTEGER NOT NULL,
                tank_id      INTEGER NOT NULL,
                quantity     INTEGER DEFAULT 1,
                created_at   TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (fish_id) REFERENCES fish(fish_id) ON DELETE CASCADE,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE,
                UNIQUE (fish_id, tank_id)
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
        """,
        "equipment": """
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                category      TEXT    NOT NULL,
                purchase_date TEXT,
                notes         TEXT,
                tank_id       INTEGER NOT NULL,
                FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
            );
        """
    }

    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_water_tests_date ON water_tests(date);",
        "CREATE INDEX IF NOT EXISTS idx_water_tests_tank_id ON water_tests(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_log_tank_id ON maintenance_log(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_cycles_tank_id ON maintenance_cycles(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_log_cycle_id ON maintenance_log(cycle_id);",
        "CREATE INDEX IF NOT EXISTS idx_custom_ranges_tank_id ON custom_ranges(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_owned_plants_tank_id ON owned_plants(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_owned_fish_tank_id ON owned_fish(tank_id);",
        "CREATE INDEX IF NOT EXISTS idx_equipment_tank_id ON equipment(tank_id);"
    ]

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

    def init_tables(self) -> None:
        """
        Initializes all database tables, creates necessary indexes, and sets up
        triggers as defined in the `TABLE_SCHEMAS`, `INDEXES`, and `TRIGGERS` attributes.
        Also inserts a 'Default Tank' if no tanks exist.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            for schema_sql in self.TABLE_SCHEMAS.values():
                cursor.execute(schema_sql)

            for idx_sql in self.INDEXES:
                cursor.execute(idx_sql)

            for trg_sql in self.TRIGGERS:
                cursor.execute(trg_sql)

            cursor.execute(
                "INSERT OR IGNORE INTO tanks (id, name) VALUES (1, 'Default Tank');"
            )
            conn.commit()