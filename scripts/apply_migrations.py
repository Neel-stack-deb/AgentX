#!/usr/bin/env python3
"""Apply SQL migrations in order. Requires DATABASE_URL (or .env in repo root)."""

import os
import re
import sys
from pathlib import Path

import psycopg

_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_file = _ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _embedding_dimension() -> str:
    raw = os.getenv("EMBEDDING_DIMENSION", "64")
    if not re.fullmatch(r"[0-9]+", raw):
        raise ValueError(f"EMBEDDING_DIMENSION must be a positive integer, got {raw!r}")
    if int(raw) < 1:
        raise ValueError("EMBEDDING_DIMENSION must be >= 1")
    return raw


def _render_sql(sql: str) -> str:
    return sql.replace("{{EMBEDDING_DIMENSION}}", _embedding_dimension())


def main() -> int:
    _load_env()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    migrations_dir = _ROOT / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print("No migration files found", file=sys.stderr)
        return 1

    index_mode = os.getenv("PGVECTOR_INDEX_MODE", "hnsw").lower()
    try:
        embedding_dim = _embedding_dimension()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agentx_schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            for path in files:
                if path.name == "003_hnsw_index.sql" and index_mode != "hnsw":
                    continue
                cur.execute(
                    "SELECT 1 FROM agentx_schema_migrations WHERE filename = %s",
                    (path.name,),
                )
                if cur.fetchone():
                    continue
                sql = _render_sql(path.read_text(encoding="utf-8"))
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO agentx_schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
                print(f"applied {path.name} (embedding_dimension={embedding_dim})")
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
