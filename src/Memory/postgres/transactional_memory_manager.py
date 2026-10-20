from datetime import datetime, timezone

from Memory.embedding_provider import EmbeddingProvider
from Memory.embedding_validation import validate_provider_embedding
from Memory.memory_manager import MemoryManager
from Memory.memory_retriever import VectorMemoryRetriever
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.retrieval import VectorIndexMetadata, VectorIndexRecord
from Types.Memory import Memory, MemoryStatus, MemoryType


class TransactionalPostgresMemoryManager(MemoryManager):
    """
    MemoryManager that persists metadata + vectors in a single PostgreSQL transaction.

    Used when MEMORY_STORE=postgres and VECTOR_STORE=pgvector share one repository.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        repository: PostgresMemoryRepository,
        memory_store,
        vector_store,
    ) -> None:
        super().__init__(
            embedding_provider=embedding_provider,
            memory_store=memory_store,
            vector_store=vector_store,
            retriever=VectorMemoryRetriever(
                embedding_provider=embedding_provider,
                vector_store=vector_store,
                memory_store=memory_store,
            ),
        )
        self._repository = repository

    def remember(
        self,
        content: str,
        *,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        source: str | None = None,
        importance: float | None = None,
        project_id: str | None = None,
        scope: str | None = None,
    ) -> Memory:
        memory = Memory(
            content=content,
            memory_type=memory_type,
            source=source,
            importance=importance,
            status=MemoryStatus.ACTIVE,
            project_id=project_id,
            scope=scope,
            embedding_model=self._embedding_provider.model_name,
            embedding_version=self._embedding_provider.model_version,
            embedding_dimension=self._embedding_provider.dimensions,
        )
        embedding = self._embedding_provider.embed(content)
        validate_provider_embedding(self._embedding_provider, embedding)
        record = self._build_index_record(memory, embedding)
        self._repository.save_memory_with_vector(memory, record)
        return memory

    def update(self, memory: Memory) -> Memory:
        if memory.status == MemoryStatus.DELETED:
            raise ValueError("cannot update a deleted memory")
        memory = memory.model_copy(
            update={
                "embedding_model": self._embedding_provider.model_name,
                "embedding_version": self._embedding_provider.model_version,
                "embedding_dimension": self._embedding_provider.dimensions,
            }
        )
        embedding = self._embedding_provider.embed(memory.content)
        validate_provider_embedding(self._embedding_provider, embedding)
        record = self._build_index_record(memory, embedding)
        updated = self._repository.update_memory_with_vector(memory, record)
        self._notify_source_memory_changed(updated.memory_id)
        return updated

    def delete(self, memory_id: str) -> bool:
        return self._repository.delete_memory(memory_id)

    def supersede(self, memory_id: str, replacement_memory_id: str) -> Memory:
        existing = self._memory_store.get(memory_id)
        if existing is None:
            raise KeyError(f"memory not found: {memory_id}")
        updated = existing.model_copy(
            update={
                "superseded_by_memory_id": replacement_memory_id,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        embedding = self._embedding_provider.embed(updated.content)
        validate_provider_embedding(self._embedding_provider, embedding)
        record = self._build_index_record(updated, embedding)
        result = self._repository.update_memory_with_vector(updated, record)
        self._notify_source_memory_changed(result.memory_id)
        return result

    def _build_index_record(
        self, memory: Memory, embedding: list[float]
    ) -> VectorIndexRecord:
        metadata = VectorIndexMetadata(
            memory_type=memory.memory_type,
            status=memory.status,
            project_id=memory.project_id,
            scope=memory.scope,
            embedding_model=memory.embedding_model or self._embedding_provider.model_name,
            embedding_version=memory.embedding_version
            or self._embedding_provider.model_version,
            embedding_dimension=memory.embedding_dimension
            or self._embedding_provider.dimensions,
            superseded_by_memory_id=memory.superseded_by_memory_id,
        )
        return VectorIndexRecord(
            memory_id=memory.memory_id,
            embedding=embedding,
            metadata=metadata,
        )
