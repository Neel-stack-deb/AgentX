from enum import Enum


class MemoryStoreKind(str, Enum):
    INMEMORY = "inmemory"
    POSTGRES = "postgres"


class VectorStoreKind(str, Enum):
    INMEMORY = "inmemory"
    PGVECTOR = "pgvector"


class PgVectorIndexMode(str, Enum):
    EXACT = "exact"
    HNSW = "hnsw"


class PgVectorDistance(str, Enum):
    COSINE = "cosine"
