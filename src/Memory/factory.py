from Memory.backend_config import (
    MemoryBackendSettings,
    MemoryStoreKind,
    VectorStoreKind,
)
from Memory.embedding_provider import EmbeddingProvider
from Memory.exceptions import DatabaseUnavailableError
from Memory.memory_manager import MemoryManager
from Memory.memory_store import InMemoryMemoryStore
from Memory.postgres.pgvector_store import PgVectorStore
from Memory.postgres.pool import create_pool
from Memory.postgres.postgres_memory_store import PostgresMemoryStore
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.postgres.transactional_memory_manager import (
    TransactionalPostgresMemoryManager,
)
from Memory.vector_store import InMemoryVectorStore


def build_memory_manager(
    embedding_provider: EmbeddingProvider,
    settings: MemoryBackendSettings | None = None,
) -> MemoryManager:
    """
    Wire MemoryManager from environment/config without Orchestrator changes.
    """
    settings = settings or MemoryBackendSettings.from_env()

    if (
        settings.memory_store == MemoryStoreKind.INMEMORY
        and settings.vector_store == VectorStoreKind.INMEMORY
    ):
        return MemoryManager(embedding_provider=embedding_provider)

    if not settings.database_url:
        raise DatabaseUnavailableError(
            "DATABASE_URL required for postgres/pgvector backends"
        )

    pool = create_pool(settings)
    repository = PostgresMemoryRepository(pool=pool, settings=settings)

    memory_store = (
        PostgresMemoryStore(repository)
        if settings.memory_store == MemoryStoreKind.POSTGRES
        else InMemoryMemoryStore()
    )
    vector_store = (
        PgVectorStore(repository)
        if settings.vector_store == VectorStoreKind.PGVECTOR
        else InMemoryVectorStore()
    )

    if (
        settings.memory_store == MemoryStoreKind.POSTGRES
        and settings.vector_store == VectorStoreKind.PGVECTOR
    ):
        return TransactionalPostgresMemoryManager(
            embedding_provider=embedding_provider,
            repository=repository,
            memory_store=memory_store,
            vector_store=vector_store,
        )

    return MemoryManager(
        embedding_provider=embedding_provider,
        memory_store=memory_store,
        vector_store=vector_store,
    )
