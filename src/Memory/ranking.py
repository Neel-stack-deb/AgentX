"""Weighted, deterministic memory ranking over vector candidates."""

from abc import ABC, abstractmethod
import math
import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from Types.Memory import Memory, RankingBreakdown, ScoredMemory


class RankingConfig(BaseModel):
    strategy_id: str = "weighted_v1"
    weight_similarity: float = 0.55
    weight_recency: float = 0.20
    weight_importance: float = 0.15
    weight_confidence: float = 0.10
    weight_lexical: float = 0.0
    recency_half_life_hours: float = 168.0
    default_importance: float = 0.5
    default_confidence: float = 0.5
    candidate_multiplier: int = Field(default=4, ge=1)
    min_candidate_pool: int = Field(default=20, ge=1)

    def candidate_pool_size(self, top_k: int) -> int:
        if top_k <= 0:
            return 0
        return max(top_k, top_k * self.candidate_multiplier, self.min_candidate_pool)


class MemoryRanker(ABC):
    @abstractmethod
    def rank(
        self,
        query: str,
        candidates: list[tuple[Memory, float]],
        *,
        top_k: int,
        now: datetime | None = None,
    ) -> list[ScoredMemory]:
        pass


class WeightedMemoryRanker(MemoryRanker):
    """
    Combines normalized signals with configurable weights.

    composite = sum(w_i * s_i) / sum(w_i) for signals with non-zero weight.
    """

    def __init__(self, config: RankingConfig | None = None) -> None:
        self._config = config or RankingConfig()

    @property
    def config(self) -> RankingConfig:
        return self._config

    def rank(
        self,
        query: str,
        candidates: list[tuple[Memory, float]],
        *,
        top_k: int,
        now: datetime | None = None,
    ) -> list[ScoredMemory]:
        if top_k <= 0:
            return []

        reference = _as_utc(now or datetime.now(timezone.utc))
        ranked: list[ScoredMemory] = []
        for memory, similarity in candidates:
            similarity_norm = _clamp01(similarity)
            recency = _recency_score(
                memory.updated_at or memory.created_at,
                reference,
                self._config.recency_half_life_hours,
            )
            importance = _clamp01(
                memory.importance
                if memory.importance is not None
                else self._config.default_importance
            )
            confidence = _clamp01(
                memory.confidence
                if memory.confidence is not None
                else self._config.default_confidence
            )
            lexical = _lexical_overlap(query, memory.content)

            composite = _weighted_composite(
                similarity_norm,
                recency,
                importance,
                confidence,
                lexical,
                self._config,
            )
            breakdown = RankingBreakdown(
                similarity=similarity_norm,
                recency=recency,
                importance=importance,
                confidence=confidence,
                lexical_overlap=lexical,
                composite=composite,
            )
            ranked.append(
                ScoredMemory(
                    memory=memory,
                    score=composite,
                    similarity_score=similarity_norm,
                    ranking_breakdown=breakdown,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                -(item.similarity_score or 0.0),
                item.memory.memory_id,
            )
        )
        return ranked[:top_k]


def _weighted_composite(
    similarity: float,
    recency: float,
    importance: float,
    confidence: float,
    lexical: float,
    config: RankingConfig,
) -> float:
    terms: list[tuple[float, float]] = [
        (config.weight_similarity, similarity),
        (config.weight_recency, recency),
        (config.weight_importance, importance),
        (config.weight_confidence, confidence),
        (config.weight_lexical, lexical),
    ]
    weight_sum = sum(weight for weight, _ in terms if weight > 0.0)
    if weight_sum == 0.0:
        return similarity
    total = sum(weight * value for weight, value in terms if weight > 0.0)
    return _clamp01(total / weight_sum)


def _recency_score(
    timestamp: datetime,
    reference: datetime,
    half_life_hours: float,
) -> float:
    if half_life_hours <= 0:
        return 1.0
    age_hours = max(
        0.0, (_as_utc(reference) - _as_utc(timestamp)).total_seconds() / 3600.0
    )
    return math.exp(-age_hours / half_life_hours)


def _lexical_overlap(query: str, content: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = _tokens(content)
    if not content_tokens:
        return 0.0
    overlap = len(query_tokens & content_tokens)
    return _clamp01(overlap / len(query_tokens))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
