from datetime import datetime, timedelta, timezone

import pytest

from Memory.embedding_provider import HashEmbeddingProvider
from Memory.memory_manager import MemoryManager
from Memory.ranking import RankingConfig, WeightedMemoryRanker
from Memory.retrieval import MemoryRetrievalFilter
from Types.Memory import Memory, MemoryStatus


def _memory(
    memory_id: str,
    content: str,
    *,
    importance: float | None = None,
    confidence: float | None = None,
    updated_at: datetime | None = None,
) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=content,
        importance=importance,
        confidence=confidence,
        updated_at=updated_at or datetime.now(timezone.utc),
        status=MemoryStatus.ACTIVE,
    )


def test_similarity_only_matches_vector_order():
    config = RankingConfig(
        weight_similarity=1.0,
        weight_recency=0.0,
        weight_importance=0.0,
        weight_confidence=0.0,
        weight_lexical=0.0,
    )
    ranker = WeightedMemoryRanker(config)
    now = datetime.now(timezone.utc)
    candidates = [
        (_memory("a", "alpha", updated_at=now - timedelta(days=30)), 0.9),
        (_memory("b", "beta", updated_at=now), 0.5),
    ]
    ranked = ranker.rank("alpha", candidates, top_k=2, now=now)
    assert [item.memory.memory_id for item in ranked] == ["a", "b"]


def test_recency_can_outrank_lower_similarity():
    config = RankingConfig(
        weight_similarity=0.2,
        weight_recency=0.8,
        weight_importance=0.0,
        weight_confidence=0.0,
        recency_half_life_hours=24.0,
    )
    ranker = WeightedMemoryRanker(config)
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    candidates = [
        (_memory("old", "topic", updated_at=now - timedelta(days=10)), 0.95),
        (_memory("new", "topic", updated_at=now - timedelta(hours=1)), 0.70),
    ]
    ranked = ranker.rank("topic", candidates, top_k=1, now=now)
    assert ranked[0].memory.memory_id == "new"


def test_importance_and_confidence_affect_order():
    config = RankingConfig(
        weight_similarity=0.0,
        weight_recency=0.0,
        weight_importance=0.6,
        weight_confidence=0.4,
        weight_lexical=0.0,
    )
    ranker = WeightedMemoryRanker(config)
    candidates = [
        (_memory("low", "x", importance=0.1, confidence=0.1), 0.5),
        (_memory("high", "x", importance=0.9, confidence=0.9), 0.5),
    ]
    ranked = ranker.rank("x", candidates, top_k=2)
    assert ranked[0].memory.memory_id == "high"


def test_stable_tie_breaking_by_memory_id():
    config = RankingConfig(
        weight_similarity=1.0,
        weight_recency=0.0,
        weight_importance=0.0,
        weight_confidence=0.0,
    )
    ranker = WeightedMemoryRanker(config)
    candidates = [
        (_memory("b-id", "same tokens here", updated_at=datetime.now(timezone.utc)), 0.8),
        (_memory("a-id", "same tokens here", updated_at=datetime.now(timezone.utc)), 0.8),
    ]
    ranked = ranker.rank("tokens", candidates, top_k=2)
    assert ranked[0].memory.memory_id == "a-id"
    assert ranked[1].memory.memory_id == "b-id"


def test_empty_candidates_returns_empty():
    ranker = WeightedMemoryRanker()
    assert ranker.rank("q", [], top_k=5) == []


def test_candidate_pool_size():
    config = RankingConfig(candidate_multiplier=4, min_candidate_pool=20)
    assert config.candidate_pool_size(5) == 20
    assert config.candidate_pool_size(10) == 40


def test_retriever_applies_ranking_and_eligibility():
    manager = MemoryManager(embedding_provider=HashEmbeddingProvider(dimensions=32))
    manager.remember("stale alpha", project_id="iso", importance=0.1)
    fresh = manager.remember(
        "fresh alpha priority",
        project_id="iso",
        importance=0.95,
    )
    outcome = manager.retrieve_with_diagnostics(
        "alpha",
        top_k=1,
        filters=MemoryRetrievalFilter(project_id="iso"),
    )
    assert outcome.memories
    assert outcome.memories[0].memory.memory_id == fresh.memory_id
    assert outcome.diagnostics.eligible_count >= 1
    assert outcome.memories[0].ranking_breakdown is not None
