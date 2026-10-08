"""
Optional local benchmark — not part of the default CI unit suite.

Run explicitly: pytest tests/benchmarks -q
"""

import os
import time

import pytest

from Memory.embedding_provider import HashEmbeddingProvider
from Memory.retrieval import VectorIndexMetadata, VectorIndexRecord
from Memory.vector_store import BruteForceVectorStore

pytestmark = pytest.mark.skipif(
    os.environ.get("AGENTX_RUN_BENCH") != "1",
    reason="set AGENTX_RUN_BENCH=1 to run vector benchmarks",
)


def test_bruteforce_scan_scales_linearly_enough_for_smoke():
    provider = HashEmbeddingProvider(dimensions=64)
    store = BruteForceVectorStore()
    n = 500
    for i in range(n):
        store.upsert(
            VectorIndexRecord(
                memory_id=str(i),
                embedding=provider.embed(f"document number {i} about agents"),
                metadata=VectorIndexMetadata(
                    embedding_model=provider.model_name,
                    embedding_version=provider.model_version,
                    embedding_dimension=provider.dimensions,
                ),
            )
        )

    query = provider.embed("agents document search")
    start = time.perf_counter()
    results = store.similarity_search(query, top_k=10)
    elapsed = time.perf_counter() - start

    assert len(results) == 10
    assert elapsed < 2.0
