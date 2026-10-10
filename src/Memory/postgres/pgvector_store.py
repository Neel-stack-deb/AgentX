from Memory.observability import observe_retrieval
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexRecord
from Memory.vector_store import VectorStore, VectorSearchStrategy


class PgVectorStore(VectorStore):
    def __init__(self, repository: PostgresMemoryRepository) -> None:
        self._repository = repository

    @property
    def search_strategy(self) -> VectorSearchStrategy:
        return self._repository.search_strategy

    def upsert(self, record: VectorIndexRecord) -> None:
        self._repository.upsert_vector(record)

    def delete(self, memory_id: str) -> bool:
        return self._repository.delete_vector(memory_id)

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[tuple[str, float]]:
        with observe_retrieval("pgvector", self.search_strategy) as obs:
            obs.top_k = top_k
            if filters is not None:
                obs.filters_applied = {
                    "project_id": filters.project_id,
                    "scope": filters.scope,
                    "memory_type": (
                        filters.memory_type.value if filters.memory_type else None
                    ),
                    "status": filters.status.value if filters.status else None,
                    "embedding_version": filters.embedding_version,
                }
            results = self._repository.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
            )
            obs.result_count = len(results)
            return results
