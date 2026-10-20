"""Hierarchical summary scopes over detailed vector memories."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from Types.Memory import Memory


class SummaryScopeType(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    TOPIC = "topic"


class SummaryStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"


class MemorySummary(BaseModel):
    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    scope_type: SummaryScopeType
    scope_id: str
    parent_summary_id: str | None = None
    content: str
    source_memory_ids: list[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    status: SummaryStatus = SummaryStatus.ACTIVE
    supersedes_summary_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HierarchicalRetrievalIntent(str, Enum):
    OVERVIEW = "overview"
    TOPIC = "topic"
    DETAIL = "detail"


class HierarchicalRetrievalResult(BaseModel):
    intent: HierarchicalRetrievalIntent
    scope_type: SummaryScopeType
    scope_id: str | None = None
    summary: MemorySummary | None = None
    detailed_memories: list[Memory] = Field(default_factory=list)
    insufficient_evidence: bool = False
    message: str | None = None
