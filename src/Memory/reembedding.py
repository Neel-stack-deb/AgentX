"""
Foundation for batch re-embedding when embedding_model/version changes.

Does not run automatically at startup or inside normal retrieval.
"""

from dataclasses import dataclass

from Memory.embedding_provider import EmbeddingProvider
from Memory.embedding_validation import validate_provider_embedding
from Memory.postgres.repository import PostgresMemoryRepository
from Memory.retrieval import VectorIndexMetadata, VectorIndexRecord
from Types.Memory import Memory


@dataclass
class ReembeddingResult:
    processed: int
    memory_ids: list[str]


class ReembeddingMigrator:
    """
    Re-embed memories still tagged with an old embedding_version.

    Intended for offline/operator-triggered jobs, not the Orchestrator.
    """

    def __init__(
        self,
        repository: PostgresMemoryRepository,
        target_provider: EmbeddingProvider,
    ) -> None:
        self._repository = repository
        self._target_provider = target_provider

    def reembed_batch(
        self,
        *,
        source_embedding_version: str,
        source_embedding_model: str | None = None,
        limit: int = 100,
    ) -> ReembeddingResult:
        memories = self._repository.list_memories_for_reembedding(
            embedding_model=source_embedding_model,
            embedding_version=source_embedding_version,
            limit=limit,
        )
        updated_ids: list[str] = []
        for memory in memories:
            embedding = self._target_provider.embed(memory.content)
            validate_provider_embedding(self._target_provider, embedding)
            memory = memory.model_copy(
                update={
                    "embedding_model": self._target_provider.model_name,
                    "embedding_version": self._target_provider.model_version,
                    "embedding_dimension": self._target_provider.dimensions,
                }
            )
            record = VectorIndexRecord(
                memory_id=memory.memory_id,
                embedding=embedding,
                metadata=VectorIndexMetadata(
                    memory_type=memory.memory_type,
                    status=memory.status,
                    project_id=memory.project_id,
                    scope=memory.scope,
                    embedding_model=memory.embedding_model,
                    embedding_version=memory.embedding_version,
                    embedding_dimension=memory.embedding_dimension,
                    superseded_by_memory_id=memory.superseded_by_memory_id,
                ),
            )
            self._repository.update_memory_with_vector(memory, record)
            updated_ids.append(memory.memory_id)
        return ReembeddingResult(processed=len(updated_ids), memory_ids=updated_ids)
