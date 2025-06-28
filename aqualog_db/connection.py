# aqualog_db/connection.py

"""
connection.py – Database Connection Manager

A simple module that provides a managed `sqlite3.Connection` to the project's
`aqualog.db` database file, ensuring a consistent and safe connection context
for all database operations.
"""

from __future__ import annotations
import sqlite3
from contextlib import contextmanager

# Import the DB_FILE constant from your central configuration
from config import DB_FILE

@contextmanager
def get_connection() -> sqlite3.Connection:
    """
    Provides a context-managed `sqlite3.Connection` to the project's `aqualog.db` file.

    This ensures the correct database path is used regardless of the current
    working directory. It also configures the connection for type parsing,
    dict-like row access, and strict foreign key enforcement. The connection
    is automatically closed upon exiting the context.

    Yields:
        sqlite3.Connection: A configured database connection object.
    """
    # Connect with type parsing and row factory for dict-like access
    conn = sqlite3.connect(
        DB_FILE,  # Use the imported DB_FILE constant
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()