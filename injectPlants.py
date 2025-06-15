"""
injectFish.py – create / refresh the master *fish* catalogue
────────────────────────────────────────────────────────────
• Creates the `fish` table (if missing) with a compatible schema
• Wipes any existing rows and resets the AUTOINCREMENT counter
• Loads records from fish.csv, skipping the CSV’s first `fish_id` column
  so SQLite can manage its own ROWID / AUTOINCREMENT key
Updated: 2025-06-15
"""
from __future__ import annotations

import csv
import os
import sqlite3
from pathlib import Path

# ───────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH   = PROJECT_ROOT / "aqualog.db"
CSV_PATH  = PROJECT_ROOT / "fish.csv"          # <-- adjust if stored elsewhere

# ───────────────────────────────────────────────────────────
# Main routine
# ───────────────────────────────────────────────────────────
def create_and_inject_data() -> None:
    """
    Ensure the `fish` table exists with the expected columns,
    then reload its contents from fish.csv.
    """
    if not CSV_PATH.exists():
        print(f"❌  Could not find fish.csv at {CSV_PATH}")
        return

    print(f"🗄️  Connecting to database: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # 1️⃣  Create table (if missing) with a schema that matches the app
        print("🔧  Ensuring `fish` table exists …")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fish (
                -- rowid (auto) will act as fish_id
                name_english       TEXT,
                name_latin         TEXT,
                common_name        TEXT DEFAULT '',       -- added for app lookups
                origin             TEXT,
                phmin              REAL,
                phmax              REAL,
                temperature_min    REAL,
                temperature_max    REAL,
                cm_max             REAL,
                tank_size_liter    REAL,
                image_url          TEXT,
                swim               INTEGER               -- 1 = bottom, 2 = mid, 3 = top
            );
            """
        )

        # 2️⃣  Clear existing rows for a clean import
        print("🧹  Clearing existing data …")
        cur.execute("DELETE FROM fish;")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='fish';")

        # 3️⃣  Read the CSV and insert
        print(f"📑  Loading {CSV_PATH.name} …")
        with CSV_PATH.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)  # skip header line

            # Header sanity check (optional but nice)
            expected = [
                "fish_id", "name_english", "name_latin", "origin", "phmin",
                "phmax", "temperature_min", "temperature_max", "cm_max",
                "tank_size_liter", "image_url", "swim"
            ]
            if header != expected:
                print(
                    "⚠️  CSV header doesn’t match expected columns.\n"
                    f"    Expected: {expected}\n"
                    f"    Found   : {header}"
                )

            insert_sql = """
                INSERT INTO fish (
                    name_english, name_latin, origin,
                    phmin, phmax, temperature_min, temperature_max,
                    cm_max, tank_size_liter, image_url, swim
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            rows = [row[1:] for row in reader if row]  # drop fish_id column
            cur.executemany(insert_sql, rows)
            print(f"✅  Inserted {len(rows)} fish.")

        conn.commit()
        print("🎉  Data injection complete.")

# ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    create_and_inject_data()
