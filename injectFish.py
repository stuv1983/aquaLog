"""
injectFish.py – Create/refresh the master fish catalogue with the correct schema.
"""
import csv
import sqlite3
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "aqualog.db"
CSV_PATH = PROJECT_ROOT / "fish.csv"

def create_and_inject_data():
    """
    Ensures the `fish` table exists with all columns and reloads its
    contents from fish.csv, mapping the columns correctly.
    """
    if not CSV_PATH.exists():
        print(f"❌ Could not find fish.csv at {CSV_PATH}")
        return

    print(f"🗄️ Connecting to database: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        print("- Dropping old fish table (if it exists)...")
        cur.execute("DROP TABLE IF EXISTS fish;")

        print("- Creating new 'fish' table with complete schema...")
        cur.execute("""
            CREATE TABLE fish (
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
        """)

        print(f"- Loading data from {CSV_PATH.name}...")
        with CSV_PATH.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            to_insert = []
            for row in reader:
                # Map CSV headers to DB columns
                to_insert.append((
                    row.get('fish_id'),
                    row.get('name_latin'),      # Maps to species_name
                    row.get('name_english'),    # Maps to common_name
                    row.get('origin'),
                    row.get('phmin'),
                    row.get('phmax'),
                    row.get('temperature_min'),
                    row.get('temperature_max'),
                    row.get('tank_size_liter'),
                    row.get('image_url'),
                    row.get('swim')
                ))

        cur.executemany(
            """
            INSERT INTO fish (
                fish_id, species_name, common_name, origin, phmin, phmax,
                temperature_min, temperature_max, tank_size_liter, image_url, swim
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            to_insert
        )
        print(f"✅ Inserted {len(to_insert)} fish records.")

        conn.commit()
        print("🎉 Data injection complete.")

if __name__ == "__main__":
    create_and_inject_data()