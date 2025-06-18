# aqualog_db/connection.py

"""
connection.py – Database Connection Manager

A simple module that provides a managed `sqlite3.Connection` to the project's
`aqualog.db` database file, ensuring a consistent and safe connection context
for all database operations.
"""

import os
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_connection():
    """
    Provides a context-managed sqlite3 Connection to the project's aqualog.db file,
    ensuring the correct database path regardless of the current working directory.
    """
    # Determine project root (parent of this module's directory)
    project_root = os.path.dirname(os.path.dirname(__file__)) #
    db_path = os.path.join(project_root, "aqualog.db") #

    # ADD THIS LINE TO REVEAL THE PATH
    print(f"--- !!! APPLICATION IS USING DATABASE AT: {db_path} !!! ---")

    # Connect with type parsing and row factory for dict-like access
    conn = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()