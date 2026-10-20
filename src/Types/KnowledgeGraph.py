"""Knowledge graph memory domain types (entities and typed relationships)."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class GraphEntity(BaseModel):
    """A node in the knowledge graph."""

    entity_id: str
    name: str
    properties: dict[str, str] = Field(default_factory=dict)
    source_memory_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphRelationship(BaseModel):
    """A directed, typed edge between two entities."""

    relationship_id: str = Field(default_factory=lambda: str(uuid4()))
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    properties: dict[str, str] = Field(default_factory=dict)
    source_memory_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphTraversalNode(BaseModel):
    """One entity reached during graph traversal."""

    entity_id: str
    depth: int
