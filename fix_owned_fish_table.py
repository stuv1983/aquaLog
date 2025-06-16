import sqlite3
import os
from aqualog_db.connection import get_connection

def rebuild_owned_fish_table():
    """
    Rebuilds the owned_fish table to include the 'id' PRIMARY KEY
    and a UNIQUE constraint, preserving all existing data.
    """
    print("Connecting to the database to fix the 'owned_fish' table schema...")
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Check if the fix has already been applied
            cur.execute("PRAGMA table_info(owned_fish);")
            current_columns = {row[1] for row in cur.fetchall()}
            if 'id' in current_columns and 'quantity' in current_columns:
                print("The 'owned_fish' table appears to be up to date. No changes needed.")
                return

            print("Step 1: Renaming original 'owned_fish' table to 'owned_fish_old'...")
            cur.execute("ALTER TABLE owned_fish RENAME TO owned_fish_old;")

            print("Step 2: Creating new 'owned_fish' table with the correct schema...")
            # FIX: Changed primary key column name to 'id' for consistency
            cur.execute("""
                CREATE TABLE owned_fish (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fish_id INTEGER NOT NULL,
                    tank_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    UNIQUE (fish_id, tank_id)
                );
            """)

            # Get the columns from the old table to copy them safely
            cur.execute("PRAGMA table_info(owned_fish_old);")
            old_columns = {row[1] for row in cur.fetchall()}
            
            # Prepare the list of columns to copy, ensuring they exist in the old table
            cols_to_copy = []
            if 'fish_id' in old_columns: cols_to_copy.append('fish_id')
            if 'tank_id' in old_columns: cols_to_copy.append('tank_id')
            if 'quantity' in old_columns: cols_to_copy.append('quantity')
            
            if not cols_to_copy:
                 raise Exception("Old owned_fish table has no recognizable columns to copy.")

            cols_str = ", ".join(cols_to_copy)
            print(f"Step 3: Copying data for columns ({cols_str}) into the new table...")
            cur.execute(f"INSERT INTO owned_fish ({cols_str}) SELECT {cols_str} FROM owned_fish_old;")

            print("Step 4: Dropping the old 'owned_fish_old' table...")
            cur.execute("DROP TABLE owned_fish_old;")

            conn.commit()
            print("\nSuccess! The 'owned_fish' table has been rebuilt correctly.")
            print("The Fish Tab should now load without any errors.")

        except sqlite3.OperationalError as e:
            if "no such table: owned_fish" in str(e):
                print("The 'owned_fish' table did not exist. Creating it fresh.")
                # If the original table doesn't exist, we just run the CREATE statement from above and commit.
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS owned_fish (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fish_id INTEGER NOT NULL,
                        tank_id INTEGER NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        UNIQUE (fish_id, tank_id)
                    );
                """)
                conn.commit()
            else:
                print(f"An unexpected database error occurred: {e}")
                conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            conn.rollback()

if __name__ == "__main__":
    rebuild_owned_fish_table()