from pydantic import BaseModel, Field

from Types.Memory import ScoredMemory


class RetrievalDiagnostics(BaseModel):
    ranking_strategy: str
    candidate_pool_size: int
    candidate_count: int
    eligible_count: int
    result_count: int = 0
    retrieval_latency_ms: float = 0.0
    ranking_latency_ms: float = 0.0


class RetrievalOutcome(BaseModel):
    memories: list[ScoredMemory] = Field(default_factory=list)
    diagnostics: RetrievalDiagnostics
