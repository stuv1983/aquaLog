# injectPlants.py (Corrected)

"""
injectPlants.py – Creates or refreshes the master 'plants' catalogue.
- Connects to the aqualog.db database.
- Drops the existing 'plants' table for a clean import.
- Creates a new 'plants' table using the schema from the main application.
- Reads records from plants.csv and inserts them into the new table.
"""
import csv
import sqlite3
from pathlib import Path

# --- Configuration ---
# This script assumes it's in the same directory as the database and CSV file.
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "aqualog.db"
CSV_PATH = PROJECT_ROOT / "plants.csv"

def inject_plant_data():
    """
    Ensures the `plants` table exists with the correct schema and reloads its
    contents from plants.csv.
    """
    if not CSV_PATH.exists():
        print(f"❌ ERROR: Could not find plants.csv at {CSV_PATH}")
        return

    print(f"🗄️  Connecting to database: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        print("-> Dropping old 'plants' table (if it exists) for a clean import...")
        cur.execute("DROP TABLE IF EXISTS plants;")

        print("-> Creating new 'plants' table with the application schema...")
        # This schema matches the one in aqualog_db/schema.py
        cur.execute("""
            CREATE TABLE plants (
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
                thumbnail_url TEXT
            );
        """)

        print(f"-> Loading data from {CSV_PATH.name}...")
        try:
            with CSV_PATH.open(newline="", encoding="utf-8-sig") as fh: # Use utf-8-sig to handle potential BOM
                reader = csv.DictReader(fh)
                
                # Prepare for insertion by dynamically getting columns from the CSV
                columns = reader.fieldnames
                if not columns:
                    print("❌ ERROR: CSV file is empty or has no header.")
                    return

                placeholders = ", ".join("?" for _ in columns)
                to_insert = [tuple(row[col] for col in columns) for row in reader]

            cur.executemany(
                f"INSERT INTO plants ({', '.join(columns)}) VALUES ({placeholders});",
                to_insert
            )
            print(f"✅ Inserted {len(to_insert)} plant records.")

            conn.commit()
            print("🎉 Plant data injection complete.")
        except Exception as e:
            print(f"❌ An error occurred during plant data injection: {e}")
            conn.rollback()

if __name__ == "__main__":
    inject_plant_data()
