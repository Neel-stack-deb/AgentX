#!/usr/bin/env python3
"""Operator command: re-embed a batch of memories for a new embedding version."""

import argparse
import os
import sys

from Memory.backend_config import MemoryBackendSettings
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.factory import build_memory_manager
from Memory.postgres.pool import create_pool
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.reembedding import ReembeddingMigrator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--source-model", default=None)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dimensions", type=int, default=64)
    parser.add_argument("--target-version", default="2")
    args = parser.parse_args()

    settings = MemoryBackendSettings.from_env()
    if not settings.database_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    pool = create_pool(settings)
    repository = PostgresMemoryRepository(pool=pool, settings=settings)
    target = HashEmbeddingProvider(
        dimensions=args.dimensions,
        model_version=args.target_version,
    )
    migrator = ReembeddingMigrator(repository=repository, target_provider=target)
    result = migrator.reembed_batch(
        source_embedding_version=args.source_version,
        source_embedding_model=args.source_model,
        limit=args.limit,
    )
    print(f"re-embedded {result.processed} memories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
