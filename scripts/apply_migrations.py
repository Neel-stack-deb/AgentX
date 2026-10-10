#!/usr/bin/env python3
"""Apply SQL migrations in order. Requires DATABASE_URL."""

import os
import sys
from pathlib import Path

import psycopg


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print("No migration files found", file=sys.stderr)
        return 1

    index_mode = os.getenv("PGVECTOR_INDEX_MODE", "hnsw").lower()
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
                if path.name == "002_hnsw_index.sql" and index_mode != "hnsw":
                    continue
                cur.execute(
                    "SELECT 1 FROM agentx_schema_migrations WHERE filename = %s",
                    (path.name,),
                )
                if cur.fetchone():
                    continue
                sql = path.read_text(encoding="utf-8")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO agentx_schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
                print(f"applied {path.name}")
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
