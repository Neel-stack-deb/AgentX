import os
import subprocess
import sys
from pathlib import Path

import pytest

from Memory.backend_config import MemoryBackendSettings
from Memory.backend_config_enums import MemoryStoreKind, PgVectorIndexMode, VectorStoreKind
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.factory import build_memory_manager
from Memory.retrieval import MemoryRetrievalFilter
from Types.Memory import MemoryType

pytestmark = pytest.mark.skipif(
    os.environ.get("AGENTX_PG_INTEGRATION") != "1",
    reason="set AGENTX_PG_INTEGRATION=1 with local Postgres",
)


@pytest.fixture(scope="module")
def pg_database_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://agentx:agentx@localhost:5432/agentx",
    )
    return url


@pytest.fixture(scope="module", autouse=True)
def apply_migrations(pg_database_url: str):
    env = os.environ.copy()
    env["DATABASE_URL"] = pg_database_url
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "apply_migrations.py")],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"migrations failed: {result.stderr}")


@pytest.fixture
def pg_manager(pg_database_url: str):
    settings = MemoryBackendSettings(
        memory_store=MemoryStoreKind.POSTGRES,
        vector_store=VectorStoreKind.PGVECTOR,
        database_url=pg_database_url,
        pgvector_index_mode=PgVectorIndexMode.HNSW,
    )
    provider = HashEmbeddingProvider(dimensions=32)
    return build_memory_manager(provider, settings=settings)


def test_pg_remember_and_retrieve(pg_manager):
    memory = pg_manager.remember(
        "postgresql vector persistence check",
        project_id="integration",
        scope="tests",
    )
    hits = pg_manager.retrieve(
        "vector persistence",
        top_k=3,
        filters=MemoryRetrievalFilter(project_id="integration", scope="tests"),
    )
    assert any(hit.memory_id == memory.memory_id for hit in hits)


def test_pg_supersede_excludes_old(pg_manager):
    old = pg_manager.remember("supersede integration old", project_id="integration")
    new = pg_manager.remember("supersede integration new", project_id="integration")
    pg_manager.supersede(old.memory_id, new.memory_id)
    hits = pg_manager.retrieve(
        "supersede integration",
        top_k=5,
        filters=MemoryRetrievalFilter(project_id="integration"),
    )
    ids = {h.memory_id for h in hits}
    assert old.memory_id not in ids


def test_pg_empty_filter_result(pg_manager):
    hits = pg_manager.retrieve(
        "nonexistent topic xyz",
        top_k=5,
        filters=MemoryRetrievalFilter(
            project_id="no-such-project",
            memory_type=MemoryType.PROCEDURAL,
        ),
    )
    assert hits == []
