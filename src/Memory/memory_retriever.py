from abc import ABC, abstractmethod

from Memory.embedding_provider import EmbeddingProvider
from Memory.memory_store import MemoryStore
from Memory.retrieval import MemoryRetrievalFilter
from Memory.vector_store import VectorStore
from Types.Memory import Memory, MemoryStatus, ScoredMemory


class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[ScoredMemory]:
        pass


class VectorMemoryRetriever(MemoryRetriever):
    """
    Embeds the query, searches the vector index, hydrates Memory records,
    and applies record-level checks (status, superseded).

    Vector similarity is candidate generation only — not final relevance ranking.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        memory_store: MemoryStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._memory_store = memory_store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[ScoredMemory]:
        query_embedding = self._embedding_provider.embed(query)
        effective_filters = filters or MemoryRetrievalFilter()

        candidates = self._vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=effective_filters,
        )

        results: list[ScoredMemory] = []
        for memory_id, score in candidates:
            memory = self._memory_store.get(memory_id)
            if memory is None:
                continue
            if memory.status != MemoryStatus.ACTIVE:
                continue
            if (
                effective_filters.exclude_superseded
                and memory.superseded_by_memory_id is not None
            ):
                continue
            results.append(ScoredMemory(memory=memory, score=score))
        return results
