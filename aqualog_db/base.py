# aqualog_db/base.py

"""
base.py – Core Database Repository Class

Provides the `BaseRepository` class, which manages thread-local SQLite
database connections. This is the foundation that all specific repository classes
inherit from to interact with the database safely and consistently.
"""

from __future__ import annotations # Added for type hinting consistency

import os
import sqlite3
import threading
import atexit
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Iterable, Set

from config import DB_FILE

class BaseRepository:
    """
    Base class for repository implementations, managing thread-local SQLite
    database connections.

    It ensures that each thread has its own database connection, handles connection
    setup (row factory, PRAGMAs), and manages connection cleanup upon program exit.
    """

    # Stores thread-local data, particularly the SQLite connection for the current thread.
    _local: threading.local = threading.local()
    # A set to keep track of all active BaseRepository instances for proper cleanup
    # of their thread-local connections when the application exits.
    _instances: Set['BaseRepository'] = set()

    def __init__(self):
        """
        Initializes a BaseRepository instance and registers it for global cleanup.
        """
        self.__class__._instances.add(self)

    @classmethod
    def _cleanup_all(cls) -> None:
        """
        Class method to close all active thread-local database connections across
        all BaseRepository instances when the program exits. This method is
        registered with `atexit` to ensure proper resource release.
        """
        for instance in cls._instances:
            instance.close_connection()

    @contextmanager
    def _connection(self) -> sqlite3.Connection:
        """
        Provides a context-managed SQLite database connection for the current thread.

        If a connection does not exist for the current thread, it establishes a new one,
        sets the row factory to `sqlite3.Row` for dict-like access, and applies necessary
        PRAGMA statements (e.g., enforcing foreign key constraints). It also handles
        transaction rollbacks on any exceptions that occur within the context block.

        Yields:
            sqlite3.Connection: A configured database connection object ready for use.

        Raises:
            RuntimeError: If a `sqlite3.Error` or any other unexpected error occurs
                          during connection setup or while executing operations within
                          the context, preventing the connection from being used reliably.
        """
        if not getattr(self._local, 'conn', None):
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            conn.row_factory = sqlite3.Row # Allows accessing columns by name
            conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
            
            # Removed PRAGMA journal_mode = WAL; and PRAGMA synchronous = NORMAL;
            # as per previous instructions to avoid deployment environment errors.
            
            self._local.conn = conn

        try:
            yield self._local.conn
        except sqlite3.Error as e:
            # Rollback any pending transaction on SQLite errors
            self._local.conn.rollback()
            raise RuntimeError(f"Database error: {e}") from e
        except Exception as e:
            # Catch other unexpected errors and rollback
            self._local.conn.rollback()
            raise RuntimeError(f"Unexpected error: {e}") from e

    def close_connection(self) -> None:
        """
        Closes the thread-local database connection if it is currently open.
        Any active transaction on this connection will be rolled back to
        prevent data inconsistencies before the connection is closed.
        """
        conn = getattr(self._local, 'conn', None)
        if conn:
            try:
                # If there's an active transaction, roll it back to prevent data inconsistencies
                if conn.in_transaction:
                    conn.rollback()
                conn.close()
            except sqlite3.Error:
                # Ignore errors during closing if the connection is already broken
                pass
            finally:
                self._local.conn = None # Clear the connection from thread-local storage

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        """
        Executes a SQL statement that does not return rows (e.g., INSERT, UPDATE, DELETE).

        Automatically commits the transaction upon successful execution.

        Args:
            sql (str): The SQL query string to execute.
            params (Iterable[Any]): A tuple or list of parameters to substitute into the query.
                                   Defaults to an empty tuple if no parameters are needed.

        Raises:
            ValueError: If a database constraint (e.g., UNIQUE, NOT NULL) is violated
                        (`sqlite3.IntegrityError`).
            RuntimeError: If a general database error occurs (`sqlite3.Error`).
        """
        with self._connection() as conn:
            try:
                conn.execute(sql, params)
                conn.commit() # Commit changes to the database
            except sqlite3.IntegrityError as e:
                # Specific error for database constraint violations
                raise ValueError(f"Constraint error: {e}") from e
            except sqlite3.Error as e:
                # General database errors
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
        """
        Executes a SQL query and returns a single row as a dictionary.

        If no rows are found matching the query, returns `None`.

        Args:
            sql (str): The SQL query string to execute.
            params (Iterable[Any]): A tuple or list of parameters to substitute into the query.
                                   Defaults to an empty tuple if no parameters are needed.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the fetched row (with column
                                      names as keys), or `None` if no row is found.

        Raises:
            RuntimeError: If a database error occurs during query execution (`sqlite3.Error`).
        """
        with self._connection() as conn:
            try:
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None # Convert sqlite3.Row object to dictionary
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        """
        Executes a SQL query and returns all matching rows as a list of dictionaries.

        If no rows are found, returns an empty list.

        Args:
            sql (str): The SQL query string to execute.
            params (Iterable[Any]): A tuple or list of parameters to substitute into the query.
                                   Defaults to an empty tuple if no parameters are needed.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents a row from the query result.

        Raises:
            RuntimeError: If a database error occurs during query execution (`sqlite3.Error`).
        """
        with self._connection() as conn:
            try:
                # Fetch all rows and convert each sqlite3.Row to a dictionary
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        """
        Executes a SQL query and returns the value of the first column
        of the first row.

        This method is particularly useful for queries that return a single
        aggregate value (e.g., `COUNT(*)`, `SUM(column)`).
        If no rows are found, returns `None`.

        Args:
            sql (str): The SQL query string to execute.
            params (Iterable[Any]): A tuple or list of parameters to substitute into the query.
                                   Defaults to an empty tuple if no parameters are needed.

        Returns:
            Any: The scalar value from the first column of the first row,
                 or `None` if no row is found. The type of the returned value
                 depends on the database column's data type.

        Raises:
            RuntimeError: If a database error occurs during query execution (`sqlite3.Error`).
        """
        with self._connection() as conn:
            try:
                row = conn.execute(sql, params).fetchone()
                return row[0] if row else None # Return the first column of the first row
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

# Ensure all connections are cleaned up when the Python interpreter exits.
# This prevents database locks and ensures proper resource release.
atexit.register(BaseRepository._cleanup_all)