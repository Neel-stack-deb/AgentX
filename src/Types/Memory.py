from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Memory(BaseModel):
    """
    A durable piece of information retained across executions.

    Schema notes:
    - memory_id: stable identifier for updates/deletes and vector index keys
    - content: searchable text payload
    - memory_type: domain category (not storage backend)
    - source: optional provenance (e.g. execution_id, user, import)
    - importance: optional 0..1 hint for future ranking (unused in v1 retrieval)
    - status: soft-delete via DELETED without dropping audit trails in MemoryStore
    - embedding_model / embedding_version / embedding_dimension: which index produced the vector
    - project_id / scope: optional tenancy or partition for retrieval filters
    - superseded_by_memory_id: when set, memory is stale; excluded from default retrieval
    """

    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    status: MemoryStatus = MemoryStatus.ACTIVE
    project_id: str | None = None
    scope: str | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    embedding_dimension: int | None = None
    superseded_by_memory_id: str | None = None


class ScoredMemory(BaseModel):
    memory: Memory
    score: float
