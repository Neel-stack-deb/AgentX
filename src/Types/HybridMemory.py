"""Combined vector + knowledge-graph retrieval result."""

from pydantic import BaseModel, Field

from Types.KnowledgeGraph import GraphEntity, GraphRelationship, GraphTraversalNode
from Types.Memory import Memory


class HybridMemoryResult(BaseModel):
    """Bounded retrieval payload: semantic memories plus graph context."""

    query: str
    memories: list[Memory] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    entities: list[GraphEntity] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)
    graph_traversal: list[GraphTraversalNode] = Field(default_factory=list)
