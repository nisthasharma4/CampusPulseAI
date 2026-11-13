"""SQLite database connection and query helpers for CampusPulse AI."""

import sqlite3
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from database.schema import create_tables
from utils.config import DB_PATH

DB_TIMEOUT_SECONDS = 30.0


def get_db_path(db_path: Optional[Union[str, Path]] = None) -> Path:
    """Return the Path object pointing to the target SQLite database file."""
    if db_path is not None:
        return Path(db_path)
    return Path(DB_PATH)


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create and return a SQLite connection with foreign keys and Row factory enabled.

    Ensures the parent directory exists before connecting.
    """
    target_path = get_db_path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=DB_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


_INITIALIZED_PATHS: set[str] = set()


def initialize_database(
    db_path: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> bool:
    """Initialize the SQLite database file and create all tables and indexes.

    Safe to call multiple times. Returns True on success, False on SQLite error.
    """
    target = str(get_db_path(db_path).resolve())
    if not force and target in _INITIALIZED_PATHS and get_db_path(db_path).exists():
        return True

    conn = None
    try:
        conn = get_connection(db_path)
        create_tables(conn)
        _INITIALIZED_PATHS.add(target)
        return True
    except sqlite3.Error as exc:
        print(f"Database initialization error: {exc}")
        return False
    finally:
        if conn is not None:
            conn.close()


def execute_query(
    query: str,
    parameters: Sequence[Any] = (),
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Execute an INSERT, UPDATE, or DELETE statement using parameterized SQL.

    Returns the last inserted row ID (or 0 if not applicable).
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.execute(query, parameters)
        conn.commit()
        return int(cursor.lastrowid or 0)
    except sqlite3.Error:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


def fetch_one(
    query: str,
    parameters: Sequence[Any] = (),
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[sqlite3.Row]:
    """Execute a SELECT query and return a single row (or None)."""
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.execute(query, parameters)
        return cursor.fetchone()
    finally:
        if conn is not None:
            conn.close()


def fetch_all(
    query: str,
    parameters: Sequence[Any] = (),
    db_path: Optional[Union[str, Path]] = None,
) -> List[sqlite3.Row]:
    """Execute a SELECT query and return all matching rows."""
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.execute(query, parameters)
        return cursor.fetchall()
    finally:
        if conn is not None:
            conn.close()


def table_exists(
    table_name: str,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Return True if the specified table exists in the SQLite database."""
    row = fetch_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?;",
        (table_name,),
        db_path=db_path,
    )
    return row is not None
