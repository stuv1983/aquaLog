
"""
injectFish.py – refreshed loader (adds scientific_name column)
───────────────────────────────────────────────────────────────
• Backs up `aqualog.db`
• Drops and recreates `fish` table with **scientific_name** plus legacy columns
• Populates scientific_name from CSV's name_latin, and copies it back into
  name_latin too, so both columns stay in sync.

Updated: 2025‑06‑15 (v1.1)
"""

from __future__ import annotations

import csv
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH      = PROJECT_ROOT / "aqualog.db"
CSV_PATH     = PROJECT_ROOT / "fish.csv"


def backup_db() -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, DB_PATH.with_name(f"aqualog_backup_{stamp}.db"))
    print("💾  Backup created.")


def reload_fish() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"fish.csv not found at {CSV_PATH}")

    columns_csv = [
        "name_english", "name_latin", "origin", "phmin", "phmax",
        "temperature_min", "temperature_max", "cm_max",
        "tank_size_liter", "image_url", "swim"
    ]

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        print("🔄  Rebuilding fish table …")
        cur.execute("DROP TABLE IF EXISTS fish;")
        cur.execute("""
            CREATE TABLE fish (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                name_english       TEXT,
                name_latin         TEXT,
                scientific_name    TEXT,
                origin             TEXT,
                phmin              REAL,
                phmax              REAL,
                temperature_min    REAL,
                temperature_max    REAL,
                cm_max             REAL,
                tank_size_liter    REAL,
                image_url          TEXT,
                swim               INTEGER,
                common_name        TEXT DEFAULT ''
            );
        """)

        ins_cols = (", ".join(columns_csv))  # insert into legacy cols
        placeholders = ", ".join(["?"] * len(columns_csv))
        insert_sql = f"INSERT INTO fish ({ins_cols}) VALUES ({placeholders});"

        rows = []
        with CSV_PATH.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)  # skip header
            for row in reader:
                if not row:
                    continue
                rows.append(row[1:])  # drop fish_id

        cur.executemany(insert_sql, rows)

        # Copy name_latin into scientific_name
        cur.execute("UPDATE fish SET scientific_name = name_latin WHERE scientific_name IS NULL OR scientific_name = '';")
        conn.commit()
        print(f"✅  Inserted {len(rows)} fish and added scientific_name column.")


if __name__ == "__main__":
    if DB_PATH.exists():
        backup_db()
    reload_fish()
    print("🎉  Fish catalogue loaded with scientific names.")
