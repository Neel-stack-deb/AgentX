from abc import ABC, abstractmethod

from Memory.embedding_provider import EmbeddingProvider
from Memory.memory_store import MemoryStore
from Memory.vector_store import VectorStore
from Types.Memory import Memory, MemoryStatus, ScoredMemory


class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[ScoredMemory]:
        pass


class VectorMemoryRetriever(MemoryRetriever):
    """
    Embeds the query, searches the vector index, hydrates Memory records,
    and filters inactive/deleted entries.
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

    def retrieve(self, query: str, top_k: int = 5) -> list[ScoredMemory]:
        query_embedding = self._embedding_provider.embed(query)
        candidates = self._vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        results: list[ScoredMemory] = []
        for memory_id, score in candidates:
            memory = self._memory_store.get(memory_id)
            if memory is None or memory.status != MemoryStatus.ACTIVE:
                continue
            results.append(ScoredMemory(memory=memory, score=score))
        return results
