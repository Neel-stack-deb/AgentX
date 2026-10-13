import logging
import time
from abc import ABC, abstractmethod

from Memory.eligibility import is_memory_eligible
from Memory.embedding_provider import EmbeddingProvider
from Memory.memory_store import MemoryStore
from Memory.ranking import MemoryRanker, RankingConfig, WeightedMemoryRanker
from Memory.retrieval import MemoryRetrievalFilter
from Memory.retrieval_outcome import RetrievalDiagnostics, RetrievalOutcome
from Memory.vector_store import VectorStore
from Types.Memory import ScoredMemory

logger = logging.getLogger("agentx.memory")


class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[ScoredMemory]:
        pass

    def retrieve_with_diagnostics(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> RetrievalOutcome:
        memories = self.retrieve(query=query, top_k=top_k, filters=filters)
        return RetrievalOutcome(
            memories=memories,
            diagnostics=RetrievalDiagnostics(
                ranking_strategy="unknown",
                candidate_pool_size=0,
                candidate_count=0,
                eligible_count=len(memories),
                result_count=len(memories),
            ),
        )


class VectorMemoryRetriever(MemoryRetriever):
    """
    Query → vector candidate pool → hard eligibility → ranking → top-K.

    Vector similarity is candidate generation only; final order uses MemoryRanker.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        memory_store: MemoryStore,
        ranker: MemoryRanker | None = None,
        ranking_config: RankingConfig | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._memory_store = memory_store
        self._ranking_config = ranking_config or RankingConfig()
        self._ranker = ranker or WeightedMemoryRanker(self._ranking_config)
        self._last_diagnostics: RetrievalDiagnostics | None = None

    @property
    def last_diagnostics(self) -> RetrievalDiagnostics | None:
        return self._last_diagnostics

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> list[ScoredMemory]:
        return self.retrieve_with_diagnostics(
            query=query, top_k=top_k, filters=filters
        ).memories

    def retrieve_with_diagnostics(
        self,
        query: str,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
    ) -> RetrievalOutcome:
        effective_filters = filters or MemoryRetrievalFilter()
        candidate_pool = self._ranking_config.candidate_pool_size(top_k)

        retrieval_start = time.perf_counter()
        query_embedding = self._embedding_provider.embed(query)
        raw_candidates = self._vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=candidate_pool,
            filters=effective_filters,
        )
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000.0

        eligible: list[tuple] = []
        for memory_id, similarity in raw_candidates:
            memory = self._memory_store.get(memory_id)
            if memory is None:
                continue
            if not is_memory_eligible(memory, effective_filters):
                continue
            eligible.append((memory, float(similarity)))

        ranking_start = time.perf_counter()
        ranked = self._ranker.rank(query, eligible, top_k=top_k)
        ranking_ms = (time.perf_counter() - ranking_start) * 1000.0

        diagnostics = RetrievalDiagnostics(
            ranking_strategy=self._ranking_config.strategy_id,
            candidate_pool_size=candidate_pool,
            candidate_count=len(raw_candidates),
            eligible_count=len(eligible),
            result_count=len(ranked),
            retrieval_latency_ms=retrieval_ms,
            ranking_latency_ms=ranking_ms,
        )
        self._last_diagnostics = diagnostics
        logger.info(
            "memory rank strategy=%s pool=%s candidates=%s eligible=%s results=%s "
            "retrieval_ms=%.2f ranking_ms=%.2f",
            diagnostics.ranking_strategy,
            diagnostics.candidate_pool_size,
            diagnostics.candidate_count,
            diagnostics.eligible_count,
            diagnostics.result_count,
            diagnostics.retrieval_latency_ms,
            diagnostics.ranking_latency_ms,
        )
        return RetrievalOutcome(memories=ranked, diagnostics=diagnostics)
