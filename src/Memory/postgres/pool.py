import re

from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from Memory.backend_config import MemoryBackendSettings
from Memory.exceptions import DatabaseUnavailableError


def _configure_connection(conn) -> None:
    register_vector(conn)

_TABLE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_table_name(name: str) -> str:
    if not _TABLE_RE.match(name):
        raise ValueError(f"invalid SQL table name: {name!r}")
    return name


def create_pool(settings: MemoryBackendSettings) -> ConnectionPool:
    if not settings.database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not configured")
    return ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.pg_pool_min_size,
        max_size=settings.pg_pool_max_size,
        timeout=settings.pg_pool_timeout_seconds,
        kwargs={"autocommit": False},
        configure=_configure_connection,
    )
