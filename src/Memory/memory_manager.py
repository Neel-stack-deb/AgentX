from datetime import datetime, timezone

from Memory.embedding_provider import EmbeddingProvider
from Memory.memory_retriever import MemoryRetriever, VectorMemoryRetriever
from Memory.memory_store import InMemoryMemoryStore, MemoryStore
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
    ) -> Memory:
        memory = Memory(
            content=content,
            memory_type=memory_type,
            source=source,
            importance=importance,
            status=MemoryStatus.ACTIVE,
        )
        embedding = self._embedding_provider.embed(content)
        self._memory_store.save(memory)
        self._vector_store.upsert(memory.memory_id, embedding)
        return memory

    def retrieve(self, query: str, top_k: int = 5) -> list[Memory]:
        scored = self._retriever.retrieve(query=query, top_k=top_k)
        return [item.memory for item in scored]

    def retrieve_scored(self, query: str, top_k: int = 5) -> list[ScoredMemory]:
        return self._retriever.retrieve(query=query, top_k=top_k)

    def update(self, memory: Memory) -> Memory:
        if memory.status == MemoryStatus.DELETED:
            raise ValueError("cannot update a deleted memory")
        updated = self._memory_store.update(memory)
        embedding = self._embedding_provider.embed(updated.content)
        self._vector_store.upsert(updated.memory_id, embedding)
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
