"""Memory persistence and retrieval errors."""


class MemoryStoreError(Exception):
    """Base class for memory backend failures."""


class MemoryNotFoundError(MemoryStoreError):
    pass


class MemoryDuplicateError(MemoryStoreError):
    pass


class EmbeddingDimensionError(MemoryStoreError):
    pass


class EmbeddingModelMismatchError(MemoryStoreError):
    pass


class VectorStoreError(MemoryStoreError):
    pass


class DatabaseUnavailableError(MemoryStoreError):
    pass


class SchemaMigrationError(MemoryStoreError):
    pass


class GraphEntityNotFoundError(MemoryStoreError):
    pass
