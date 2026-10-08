from abc import ABC, abstractmethod
from enum import Enum

from Memory.retrieval import (
    MemoryRetrievalFilter,
    VectorIndexRecord,
    metadata_matches_filter,
)
from Memory.vector_math import cosine_similarity


class VectorSearchStrategy(str, Enum):
    """Describes how a VectorStore implementation answers similarity queries."""

    BRUTE_FORCE = "brute_force"
    ANN = "ann"


class VectorStore(ABC):
    """
    Stores embeddings and answers similarity queries. No agent logic.

    Implementations may use brute-force scan (O(N×D)) or ANN (HNSW, IVF, etc.).
    Callers depend only on this interface.
    """

    @property
    @abstractmethod
    def search_strategy(self) -> VectorSearchStrategy:
        pass

    @abstractmethod
    def upsert(self, record: VectorIndexRecord) -> None:
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[tuple[str, float]]:
        """Returns (memory_id, score) pairs ordered by descending similarity."""
        pass


class BruteForceVectorStore(VectorStore):
    """
    Exact cosine similarity over all indexed vectors (O(N × D)).

    Serves as the reference implementation and the default dev backend.
    ANN backends should implement VectorStore separately with the same contract.
    """

    @property
    def search_strategy(self) -> VectorSearchStrategy:
        return VectorSearchStrategy.BRUTE_FORCE

    def __init__(self) -> None:
        self._records: dict[str, VectorIndexRecord] = {}

    def upsert(self, record: VectorIndexRecord) -> None:
        self._records[record.memory_id] = record

    def delete(self, memory_id: str) -> bool:
        return self._records.pop(memory_id, None) is not None

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[tuple[str, float]]:
        if top_k <= 0:
            return []

        scored: list[tuple[str, float]] = []
        for memory_id, record in self._records.items():
            if not metadata_matches_filter(record.metadata, filters):
                continue
            score = cosine_similarity(query_embedding, record.embedding)
            scored.append((memory_id, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class InMemoryVectorStore(BruteForceVectorStore):
    """Alias for the in-process brute-force index (replaceable)."""

    pass
