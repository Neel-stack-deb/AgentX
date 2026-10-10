import os

from pydantic import BaseModel, Field

from Memory.backend_config_enums import (
    MemoryStoreKind,
    PgVectorDistance,
    PgVectorIndexMode,
    VectorStoreKind,
)


class MemoryBackendSettings(BaseModel):
    """
    Environment-driven wiring for memory backends.

    Orchestrator code does not read these; use build_memory_manager().
    """

    memory_store: MemoryStoreKind = MemoryStoreKind.INMEMORY
    vector_store: VectorStoreKind = VectorStoreKind.INMEMORY
    database_url: str | None = None
    pg_table: str = "agentx_memories"
    pg_pool_min_size: int = 1
    pg_pool_max_size: int = 10
    pg_pool_timeout_seconds: float = 30.0
    pgvector_index_mode: PgVectorIndexMode = PgVectorIndexMode.HNSW
    pgvector_distance: PgVectorDistance = PgVectorDistance.COSINE
    hnsw_ef_search: int = 40

    @classmethod
    def from_env(cls) -> "MemoryBackendSettings":
        return cls(
            memory_store=MemoryStoreKind(os.getenv("MEMORY_STORE", "inmemory")),
            vector_store=VectorStoreKind(os.getenv("VECTOR_STORE", "inmemory")),
            database_url=os.getenv("DATABASE_URL"),
            pg_table=os.getenv("PGVECTOR_TABLE", "agentx_memories"),
            pg_pool_min_size=int(os.getenv("PG_POOL_MIN_SIZE", "1")),
            pg_pool_max_size=int(os.getenv("PG_POOL_MAX_SIZE", "10")),
            pg_pool_timeout_seconds=float(os.getenv("PG_POOL_TIMEOUT_SECONDS", "30")),
            pgvector_index_mode=PgVectorIndexMode(
                os.getenv("PGVECTOR_INDEX_MODE", "hnsw")
            ),
            pgvector_distance=PgVectorDistance(os.getenv("PGVECTOR_DISTANCE", "cosine")),
            hnsw_ef_search=int(os.getenv("PGVECTOR_HNSW_EF_SEARCH", "40")),
        )
