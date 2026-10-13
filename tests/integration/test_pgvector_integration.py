import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

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
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://agentx:agentx@localhost:5432/agentx",
    )
    return url


@pytest.fixture(scope="module", autouse=True)
def apply_migrations(pg_database_url: str):
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    env = os.environ.copy()
    env["DATABASE_URL"] = pg_database_url
    env.setdefault("EMBEDDING_DIMENSION", "64")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "apply_migrations.py")],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"migrations failed (exit {result.returncode}):\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest.fixture
def pg_manager(pg_database_url: str):
    settings = MemoryBackendSettings(
        memory_store=MemoryStoreKind.POSTGRES,
        vector_store=VectorStoreKind.PGVECTOR,
        database_url=pg_database_url,
        pgvector_index_mode=PgVectorIndexMode.HNSW,
    )
    provider = HashEmbeddingProvider(dimensions=64)
    return build_memory_manager(provider, settings=settings)


def test_pg_remember_and_retrieve(pg_manager):
    # Unique project scope so prior integration runs cannot crowd out top-K.
    project_id = f"remember-{uuid.uuid4()}"
    content = f"postgresql vector persistence check {project_id}"
    memory = pg_manager.remember(
        content,
        project_id=project_id,
        scope="tests",
    )
    hits = pg_manager.retrieve(
        content,
        top_k=5,
        filters=MemoryRetrievalFilter(project_id=project_id, scope="tests"),
    )
    assert hits, "expected at least one hit in isolated project scope"
    assert any(hit.memory_id == memory.memory_id for hit in hits)


def test_pg_supersede_excludes_old(pg_manager):
    project_id = f"supersede-{uuid.uuid4()}"
    old = pg_manager.remember(
        f"supersede integration old {project_id}", project_id=project_id
    )
    new = pg_manager.remember(
        f"supersede integration new {project_id}", project_id=project_id
    )
    pg_manager.supersede(old.memory_id, new.memory_id)
    hits = pg_manager.retrieve(
        f"supersede integration {project_id}",
        top_k=5,
        filters=MemoryRetrievalFilter(project_id=project_id),
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
