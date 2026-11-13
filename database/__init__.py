"""Database package for CampusPulse AI."""

from database.db import (
    execute_query,
    fetch_all,
    fetch_one,
    get_connection,
    get_db_path,
    initialize_database,
    table_exists,
)
from database.schema import REQUIRED_TABLES, SCHEMA_VERSION, create_tables

__all__ = [
    "REQUIRED_TABLES",
    "SCHEMA_VERSION",
    "create_tables",
    "execute_query",
    "fetch_all",
    "fetch_one",
    "get_connection",
    "get_db_path",
    "initialize_database",
    "table_exists",
]
