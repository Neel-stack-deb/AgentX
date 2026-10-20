from datetime import datetime, timezone
from typing import TYPE_CHECKING

from Memory.embedding_provider import EmbeddingProvider
from Memory.embedding_validation import validate_provider_embedding
from Memory.memory_retriever import MemoryRetriever, VectorMemoryRetriever
from Memory.ranking import RankingConfig
from Memory.retrieval_outcome import RetrievalOutcome
from Memory.memory_store import InMemoryMemoryStore, MemoryStore
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexMetadata, VectorIndexRecord
from Memory.vector_store import InMemoryVectorStore, VectorStore
from Types.Memory import Memory, MemoryStatus, MemoryType, ScoredMemory

if TYPE_CHECKING:
    from Memory.hierarchical.summary_store import HierarchicalSummaryStore
    from Memory.knowledge_graph.knowledge_graph_store import KnowledgeGraphStore
    from Types.HierarchicalMemory import (
        HierarchicalRetrievalIntent,
        HierarchicalRetrievalResult,
        MemorySummary,
        SummaryScopeType,
    )
    from Types.HybridMemory import HybridMemoryResult


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
        ranking_config: RankingConfig | None = None,
        summary_store: "HierarchicalSummaryStore | None" = None,
        knowledge_graph: "KnowledgeGraphStore | None" = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._memory_store = memory_store or InMemoryMemoryStore()
        self._vector_store = vector_store or InMemoryVectorStore()
        self._summary_store = summary_store
        self._knowledge_graph = knowledge_graph
        self._ranking_config = ranking_config or RankingConfig()
        self._retriever = retriever or VectorMemoryRetriever(
            embedding_provider=self._embedding_provider,
            vector_store=self._vector_store,
            memory_store=self._memory_store,
            ranking_config=self._ranking_config,
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
        validate_provider_embedding(self._embedding_provider, embedding)
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

    def retrieve_hybrid(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
        graph_max_depth: int = 2,
        relationship_type: str | None = None,
    ) -> "HybridMemoryResult":
        """
        Bounded hybrid retrieval (vector memories + graph context).

        Does not mutate execution context; callers inject into prompts if needed.
        """
        if self._knowledge_graph is None:
            raise RuntimeError("knowledge_graph is not configured on MemoryManager")
        from Memory.hybrid.hybrid_memory import HybridMemoryRetriever

        return HybridMemoryRetriever(
            memory_retriever=self._retriever,
            knowledge_graph=self._knowledge_graph,
        ).retrieve(
            query,
            top_k=top_k,
            filters=filters,
            graph_max_depth=graph_max_depth,
            relationship_type=relationship_type,
        )

    def retrieve_hierarchical(
        self,
        intent: "HierarchicalRetrievalIntent",
        *,
        scope_type: "SummaryScopeType",
        scope_id: str,
        topic_scope_id: str | None = None,
    ) -> "HierarchicalRetrievalResult":
        if self._summary_store is None:
            raise RuntimeError("summary_store is not configured on MemoryManager")
        from Memory.hierarchical.hierarchical_retriever import HierarchicalMemoryRetriever
        from Types.HierarchicalMemory import HierarchicalRetrievalResult

        return HierarchicalMemoryRetriever(
            summary_store=self._summary_store,
            memory_store=self._memory_store,
        ).retrieve(
            intent,
            scope_type=scope_type,
            scope_id=scope_id,
            topic_scope_id=topic_scope_id,
        )

    def retrieve_with_diagnostics(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> RetrievalOutcome:
        if hasattr(self._retriever, "retrieve_with_diagnostics"):
            return self._retriever.retrieve_with_diagnostics(
                query=query, top_k=top_k, filters=filters
            )
        memories = self.retrieve_scored(query=query, top_k=top_k, filters=filters)
        from Memory.retrieval_outcome import RetrievalDiagnostics

        return RetrievalOutcome(
            memories=memories,
            diagnostics=RetrievalDiagnostics(
                ranking_strategy="passthrough",
                candidate_pool_size=top_k,
                candidate_count=len(memories),
                eligible_count=len(memories),
                result_count=len(memories),
            ),
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
        validate_provider_embedding(self._embedding_provider, embedding)
        self._index_memory(updated, embedding)
        self._notify_source_memory_changed(updated.memory_id)
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
        self._notify_source_memory_changed(updated.memory_id)
        return updated

    def invalidate_dependent_summaries(self, memory_id: str) -> list["MemorySummary"]:
        """
        Mark summaries that cite ``memory_id`` as stale.

        Use when repository change-tracking cannot detect updates automatically.
        """
        if self._summary_store is None:
            return []
        return self._summary_store.mark_stale_for_memory(memory_id)

    def regenerate_summary(self, summary_id: str, new_content: str) -> "MemorySummary":
        if self._summary_store is None:
            raise RuntimeError("summary_store is not configured on MemoryManager")
        return self._summary_store.regenerate(summary_id, new_content)

    def _notify_source_memory_changed(self, memory_id: str) -> None:
        self.invalidate_dependent_summaries(memory_id)

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
