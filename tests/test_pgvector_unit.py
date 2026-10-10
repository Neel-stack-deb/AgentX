from unittest.mock import MagicMock

import pytest

from Memory.backend_config import MemoryBackendSettings
from Memory.exceptions import EmbeddingDimensionError
from Memory.backend_config_enums import PgVectorIndexMode
from Memory.postgres.pgvector_store import PgVectorStore
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexMetadata, VectorIndexRecord
from Memory.vector_store import VectorSearchStrategy
from Types.Memory import MemoryStatus, MemoryType


def test_pgvector_store_delegates_search_strategy():
    repo = MagicMock(spec=PostgresMemoryRepository)
    repo.search_strategy = VectorSearchStrategy.ANN
    store = PgVectorStore(repo)
    assert store.search_strategy == VectorSearchStrategy.ANN


def test_pgvector_store_similarity_search_delegates():
    repo = MagicMock(spec=PostgresMemoryRepository)
    repo.search_strategy = VectorSearchStrategy.BRUTE_FORCE
    repo.similarity_search.return_value = [("id-1", 0.9)]
    store = PgVectorStore(repo)
    results = store.similarity_search([0.1, 0.2], top_k=3, filters=None)
    assert results == [("id-1", 0.9)]
    repo.similarity_search.assert_called_once()


def test_repository_filter_clause_excludes_superseded():
    settings = MemoryBackendSettings(
        database_url="postgresql://x",
        pgvector_index_mode=PgVectorIndexMode.EXACT,
    )
    repo = PostgresMemoryRepository(pool=MagicMock(), settings=settings)
    sql, params = repo._build_filter_clause(MemoryRetrievalFilter())
    assert "superseded_by_memory_id IS NULL" in sql
    assert MemoryStatus.ACTIVE.value in params


def test_upsert_vector_validates_dimension():
    settings = MemoryBackendSettings(database_url="postgresql://x")
    repo = PostgresMemoryRepository(pool=MagicMock(), settings=settings)
    record = VectorIndexRecord(
        memory_id="00000000-0000-0000-0000-000000000001",
        embedding=[0.1, 0.2],
        metadata=VectorIndexMetadata(
            embedding_model="hash-bow",
            embedding_version="1",
            embedding_dimension=32,
            memory_type=MemoryType.SEMANTIC,
            status=MemoryStatus.ACTIVE,
        ),
    )
    with pytest.raises(EmbeddingDimensionError):
        repo.upsert_vector(record)
