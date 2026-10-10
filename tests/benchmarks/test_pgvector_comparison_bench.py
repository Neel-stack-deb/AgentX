"""
Compare in-memory brute-force vs pgvector exact vs pgvector HNSW.

Run: AGENTX_RUN_BENCH=1 AGENTX_PG_INTEGRATION=1 pytest tests/benchmarks/test_pgvector_comparison_bench.py -s
"""

import os
import statistics
import time

import pytest

from Memory.backend_config import MemoryBackendSettings
from Memory.backend_config_enums import MemoryStoreKind, PgVectorIndexMode, VectorStoreKind
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.factory import build_memory_manager
from Memory.retrieval import VectorIndexMetadata, VectorIndexRecord
from Memory.vector_store import BruteForceVectorStore

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("AGENTX_RUN_BENCH") != "1",
        reason="set AGENTX_RUN_BENCH=1",
    ),
    pytest.mark.skipif(
        os.environ.get("AGENTX_PG_INTEGRATION") != "1",
        reason="set AGENTX_PG_INTEGRATION=1 for pgvector benchmarks",
    ),
]


def _populate_bruteforce(n: int, provider: HashEmbeddingProvider):
    store = BruteForceVectorStore()
    for i in range(n):
        store.upsert(
            VectorIndexRecord(
                memory_id=str(i),
                embedding=provider.embed(f"doc {i} about agents and memory"),
                metadata=VectorIndexMetadata(
                    embedding_model=provider.model_name,
                    embedding_version=provider.model_version,
                    embedding_dimension=provider.dimensions,
                ),
            )
        )
    return store


def _latency_ms(fn, repeats: int = 5) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def test_compare_backends_latency_smoke():
    n = int(os.environ.get("AGENTX_BENCH_N", "200"))
    top_k = 10
    provider = HashEmbeddingProvider(dimensions=64)
    query = provider.embed("agents memory search")

    brute = _populate_bruteforce(n, provider)
    brute_ms = _latency_ms(lambda: brute.similarity_search(query, top_k=top_k))

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://agentx:agentx@localhost:5432/agentx",
    )

    for mode in (PgVectorIndexMode.EXACT, PgVectorIndexMode.HNSW):
        settings = MemoryBackendSettings(
            memory_store=MemoryStoreKind.POSTGRES,
            vector_store=VectorStoreKind.PGVECTOR,
            database_url=url,
            pgvector_index_mode=mode,
        )
        manager = build_memory_manager(provider, settings=settings)
        for i in range(n):
            manager.remember(
                f"pg doc {i} about agents and memory",
                project_id=f"bench-{mode.value}",
            )
        pg_ms = _latency_ms(
            lambda: manager.retrieve(
                "agents memory search",
                top_k=top_k,
                filters=None,
            )
        )
        print(f"n={n} mode={mode.value} brute_ms={brute_ms:.2f} pg_ms={pg_ms:.2f}")
