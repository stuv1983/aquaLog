import sqlite3
import os
from aqualog_db.connection import get_connection

def migrate_and_rebuild_fish_table():
    """
    Rebuilds the fish table from the old schema to the new one,
    adding fish_id and mapping old column names to the new names.
    """
    print("Connecting to the database to migrate the 'fish' table schema...")
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Check if the fix has already been applied by looking for a new column
            cur.execute("PRAGMA table_info(fish);")
            current_columns = {row[1] for row in cur.fetchall()}
            if 'species_name' in current_columns and 'fish_id' in current_columns:
                print("Table already appears to have the new schema. No changes made.")
                return

            print("Step 1: Renaming original 'fish' table to 'fish_old'...")
            cur.execute("ALTER TABLE fish RENAME TO fish_old;")

            print("Step 2: Creating new 'fish' table with the modern schema...")
            cur.execute("""
                CREATE TABLE fish (
                    fish_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_name TEXT NOT NULL,
                    common_name TEXT,
                    origin TEXT,
                    temperament TEXT,
                    max_size_cm REAL,
                    diet TEXT,
                    min_tank_size_l INTEGER,
                    thumbnail_url TEXT,
                    notes TEXT
                );
            """)

            print("Step 3: Copying and mapping data from the old table to the new one...")
            # This statement explicitly maps the old column names to the new ones.
            cur.execute("""
                INSERT INTO fish (
                    species_name, common_name, origin, max_size_cm, 
                    min_tank_size_l, thumbnail_url
                )
                SELECT 
                    scientific_name, name_english, origin, cm_max, 
                    tank_size_liter, image_url
                FROM fish_old;
            """)

            print("Step 4: Dropping the old 'fish_old' table...")
            cur.execute("DROP TABLE fish_old;")

            conn.commit()
            print("\nSuccess! The 'fish' table has been rebuilt with the correct modern schema.")
            print("Your existing data has been migrated to the new column names.")
            print("The application will now work correctly.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Rolling back any changes.")
            conn.rollback()

if __name__ == "__main__":
    migrate_and_rebuild_fish_table()