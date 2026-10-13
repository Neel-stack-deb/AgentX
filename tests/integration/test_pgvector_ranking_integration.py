import os
import uuid

import pytest
from dotenv import load_dotenv

from Memory.backend_config import MemoryBackendSettings
from Memory.backend_config_enums import MemoryStoreKind, PgVectorIndexMode, VectorStoreKind
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.factory import build_memory_manager
from Memory.retrieval import MemoryRetrievalFilter

pytestmark = pytest.mark.skipif(
    os.environ.get("AGENTX_PG_INTEGRATION") != "1",
    reason="set AGENTX_PG_INTEGRATION=1 with local Postgres",
)


@pytest.fixture
def pg_manager():
    load_dotenv()
    settings = MemoryBackendSettings(
        memory_store=MemoryStoreKind.POSTGRES,
        vector_store=VectorStoreKind.PGVECTOR,
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://agentx:agentx@localhost:5432/agentx"
        ),
        pgvector_index_mode=PgVectorIndexMode.HNSW,
    )
    return build_memory_manager(HashEmbeddingProvider(dimensions=64), settings=settings)


def test_pg_ranking_returns_diagnostics(pg_manager):
    project_id = f"rank-{uuid.uuid4()}"
    text = f"ranking integration memory {project_id}"
    pg_manager.remember(text, project_id=project_id, importance=0.9)
    outcome = pg_manager.retrieve_with_diagnostics(
        text,
        top_k=1,
        filters=MemoryRetrievalFilter(project_id=project_id),
    )
    assert outcome.memories
    assert outcome.diagnostics.result_count == 1
    assert outcome.diagnostics.ranking_strategy == "weighted_v1"
