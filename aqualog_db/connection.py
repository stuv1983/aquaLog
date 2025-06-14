# aqualog_db/connection.py
"""
Helper module for acquiring database connections using BaseRepository
"""
from .base import BaseRepository


def get_connection():
    """
    Returns a context manager yielding a sqlite3.Connection with PRAGMAs applied.

    Usage:
        from aqualog_db.connection import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            # ... execute queries, commit as needed
    """
    return BaseRepository()._connection()
