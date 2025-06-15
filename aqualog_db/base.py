"""
base.py – Core DB functionality with connection pooling, migrations, and cleanup.
"""

import os
import sqlite3
import threading
import atexit
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Iterable, Set

from config import DB_FILE

class BaseRepository:
    """Base class for repository implementations with thread-local connections."""

    _local = threading.local()
    _instances: Set['BaseRepository'] = set()

    def __init__(self):
        self.__class__._instances.add(self)

    @classmethod
    def _cleanup_all(cls):
        """Close all live connections when program exits."""
        for instance in cls._instances:
            instance.close_connection()

    @contextmanager
    def _connection(self) -> sqlite3.Connection:
        """Provide a managed sqlite3.Connection (with PRAGMAs applied)."""
        if not getattr(self._local, 'conn', None):
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # FIX: Removed WAL pragma as it causes a disk I/O error in the deployment environment.
            # conn.execute("PRAGMA journal_mode = WAL;") 
            
            conn.execute("PRAGMA synchronous = NORMAL;")
            self._local.conn = conn

        try:
            yield self._local.conn
        except sqlite3.Error as e:
            # rollback on any DB error
            self._local.conn.rollback()
            raise RuntimeError(f"Database error: {e}") from e
        except Exception as e:
            self._local.conn.rollback()
            raise RuntimeError(f"Unexpected error: {e}") from e

    def close_connection(self):
        """Close the thread-local connection if open."""
        conn = getattr(self._local, 'conn', None)
        if conn:
            try:
                if conn.in_transaction:
                    conn.rollback()
                conn.close()
            except sqlite3.Error:
                pass
            finally:
                self._local.conn = None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        """Execute a statement without returning rows."""
        with self._connection() as conn:
            try:
                conn.execute(sql, params)
                conn.commit()
            except sqlite3.IntegrityError as e:
                raise ValueError(f"Constraint error: {e}") from e
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dict (or None)."""
        with self._connection() as conn:
            try:
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dicts."""
        with self._connection() as conn:
            try:
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

    def fetch_scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        """Execute a query and return the first column of the first row."""
        with self._connection() as conn:
            try:
                row = conn.execute(sql, params).fetchone()
                return row[0] if row else None
            except sqlite3.Error as e:
                raise RuntimeError(f"Database error: {e}") from e

# Ensure all connections are cleaned up at exit
atexit.register(BaseRepository._cleanup_all)