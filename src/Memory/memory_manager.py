from datetime import datetime, timezone

from Memory.embedding_provider import EmbeddingProvider
from Memory.memory_retriever import MemoryRetriever, VectorMemoryRetriever
from Memory.memory_store import InMemoryMemoryStore, MemoryStore
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexMetadata, VectorIndexRecord
from Memory.vector_store import InMemoryVectorStore, VectorStore
from Types.Memory import Memory, MemoryStatus, MemoryType, ScoredMemory


class MemoryManager:
    """
    Coordinates remember/retrieve/update/delete across MemoryStore, VectorStore,
    and EmbeddingProvider. Does not control execution flow or build LLM prompts.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        memory_store: MemoryStore | None = None,
        vector_store: VectorStore | None = None,
        retriever: MemoryRetriever | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._memory_store = memory_store or InMemoryMemoryStore()
        self._vector_store = vector_store or InMemoryVectorStore()
        self._retriever = retriever or VectorMemoryRetriever(
            embedding_provider=self._embedding_provider,
            vector_store=self._vector_store,
            memory_store=self._memory_store,
        )

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
        self._memory_store.save(memory)
        self._index_memory(memory, embedding)
        return memory

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[Memory]:
        scored = self._retriever.retrieve(
            query=query, top_k=top_k, filters=filters
        )
        return [item.memory for item in scored]

    def retrieve_scored(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[ScoredMemory]:
        return self._retriever.retrieve(
            query=query, top_k=top_k, filters=filters
        )

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
        updated = self._memory_store.update(memory)
        embedding = self._embedding_provider.embed(updated.content)
        self._index_memory(updated, embedding)
        return updated

    def delete(self, memory_id: str) -> bool:
        removed_from_index = self._vector_store.delete(memory_id)
        marked = self._memory_store.delete(memory_id)
        return removed_from_index or marked

    def touch_content(self, memory_id: str, content: str) -> Memory:
        existing = self._memory_store.get(memory_id)
        if existing is None:
            raise KeyError(f"memory not found: {memory_id}")
        updated = existing.model_copy(
            update={
                "content": content,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        return self.update(updated)

    def supersede(self, memory_id: str, replacement_memory_id: str) -> Memory:
        """
        Mark a memory as stale (superseded). Excluded from default retrieval.

        Full lifecycle policies (auto-archive, compression) belong here later.
        """
        existing = self._memory_store.get(memory_id)
        if existing is None:
            raise KeyError(f"memory not found: {memory_id}")
        updated = existing.model_copy(
            update={
                "superseded_by_memory_id": replacement_memory_id,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        updated = self._memory_store.update(updated)
        embedding = self._embedding_provider.embed(updated.content)
        self._index_memory(updated, embedding)
        return updated

    def _index_memory(self, memory: Memory, embedding: list[float]) -> None:
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
        self._vector_store.upsert(
            VectorIndexRecord(
                memory_id=memory.memory_id,
                embedding=embedding,
                metadata=metadata,
            )
        )
