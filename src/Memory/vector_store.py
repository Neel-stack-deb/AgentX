from abc import ABC, abstractmethod

from Memory.vector_math import cosine_similarity


class VectorStore(ABC):
    """Stores embeddings and answers similarity queries. No agent logic."""

    @abstractmethod
    def upsert(self, memory_id: str, embedding: list[float]) -> None:
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    def similarity_search(
        self, query_embedding: list[float], top_k: int
    ) -> list[tuple[str, float]]:
        """Returns (memory_id, score) pairs ordered by descending similarity."""
        pass


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._embeddings: dict[str, list[float]] = {}

    def upsert(self, memory_id: str, embedding: list[float]) -> None:
        self._embeddings[memory_id] = list(embedding)

    def delete(self, memory_id: str) -> bool:
        return self._embeddings.pop(memory_id, None) is not None

    def similarity_search(
        self, query_embedding: list[float], top_k: int
    ) -> list[tuple[str, float]]:
        if top_k <= 0:
            return []

        scored: list[tuple[str, float]] = []
        for memory_id, embedding in self._embeddings.items():
            score = cosine_similarity(query_embedding, embedding)
            scored.append((memory_id, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
