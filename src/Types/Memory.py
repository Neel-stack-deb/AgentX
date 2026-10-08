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
    """

    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    status: MemoryStatus = MemoryStatus.ACTIVE


class ScoredMemory(BaseModel):
    memory: Memory
    score: float
