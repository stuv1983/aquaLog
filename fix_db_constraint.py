import sqlite3
import os
from aqualog_db.connection import get_connection

def fix_owned_plants_constraint():
    """
    Rebuilds the owned_plants table to include the composite
    PRIMARY KEY constraint, preserving all existing data.
    """
    print("Connecting to the database to fix the 'owned_plants' table schema...")
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            print("Step 1: Renaming original 'owned_plants' table to 'owned_plants_old'...")
            cur.execute("ALTER TABLE owned_plants RENAME TO owned_plants_old;")

            print("Step 2: Creating new 'owned_plants' table with the correct PRIMARY KEY...")
            # This version includes the PRIMARY KEY on both columns.
            cur.execute("""
                CREATE TABLE owned_plants (
                    plant_id INTEGER NOT NULL,
                    tank_id INTEGER NOT NULL DEFAULT 1,
                    common_name TEXT DEFAULT '',
                    PRIMARY KEY (plant_id, tank_id)
                );
            """)

            print("Step 3: Copying data from the old table to the new one...")
            # This handles both old and new schemas gracefully.
            cur.execute("""
                INSERT INTO owned_plants (plant_id, tank_id, common_name)
                SELECT plant_id, COALESCE(tank_id, 1), COALESCE(common_name, '')
                FROM owned_plants_old;
            """)

            print("Step 4: Dropping the old 'owned_plants_old' table...")
            cur.execute("DROP TABLE owned_plants_old;")

            conn.commit()
            print("\nSuccess! The 'owned_plants' table has been rebuilt correctly.")
            print("The 'Add Plant' button should now work without errors.")

        except sqlite3.OperationalError as e:
            if "no such table: owned_plants" in str(e):
                print("Could not find the 'owned_plants' table. It may have been fixed already.")
                # If the first step fails, it might be because the fix was already run.
                # We can try to clean up a potentially leftover _old table.
                try:
                    cur.execute("DROP TABLE IF EXISTS owned_plants_old;")
                except:
                    pass
            else:
                print(f"An unexpected database error occurred: {e}")
                print("Rolling back changes.")
                conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Rolling back changes.")
            conn.rollback()

if __name__ == "__main__":
    fix_owned_plants_constraint()