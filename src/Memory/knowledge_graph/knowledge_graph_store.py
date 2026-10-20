"""In-memory knowledge graph storage and traversal."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque

from Memory.exceptions import GraphEntityNotFoundError
from Types.KnowledgeGraph import GraphEntity, GraphRelationship, GraphTraversalNode


class KnowledgeGraphStore(ABC):
    """Persistence contract for entity-relationship memory."""

    @abstractmethod
    def upsert_entity(self, entity: GraphEntity) -> GraphEntity:
        ...

    @abstractmethod
    def get_entity(self, entity_id: str) -> GraphEntity | None:
        ...

    @abstractmethod
    def add_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        ...

    @abstractmethod
    def get_neighbors(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        outgoing: bool = True,
        incoming: bool = False,
    ) -> list[str]:
        ...

    @abstractmethod
    def traverse_bfs(
        self,
        start_entity_id: str,
        max_depth: int,
        *,
        relationship_type: str | None = None,
    ) -> list[GraphTraversalNode]:
        ...


class InMemoryKnowledgeGraphStore(KnowledgeGraphStore):
    """Adjacency-list graph held in process memory (educational default)."""

    def __init__(self) -> None:
        self._entities: dict[str, GraphEntity] = {}
        self._relationships: list[GraphRelationship] = []

    def upsert_entity(self, entity: GraphEntity) -> GraphEntity:
        self._entities[entity.entity_id] = entity
        return entity

    def get_entity(self, entity_id: str) -> GraphEntity | None:
        return self._entities.get(entity_id)

    def add_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        if relationship.source_entity_id not in self._entities:
            raise GraphEntityNotFoundError(
                f"source entity not found: {relationship.source_entity_id}"
            )
        if relationship.target_entity_id not in self._entities:
            raise GraphEntityNotFoundError(
                f"target entity not found: {relationship.target_entity_id}"
            )
        self._relationships.append(relationship)
        return relationship

    def get_neighbors(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        outgoing: bool = True,
        incoming: bool = False,
    ) -> list[str]:
        if entity_id not in self._entities:
            raise GraphEntityNotFoundError(f"entity not found: {entity_id}")
        neighbors: list[str] = []
        seen: set[str] = set()
        for rel in self._relationships:
            if relationship_type is not None and rel.relationship_type != relationship_type:
                continue
            if outgoing and rel.source_entity_id == entity_id:
                if rel.target_entity_id not in seen:
                    seen.add(rel.target_entity_id)
                    neighbors.append(rel.target_entity_id)
            if incoming and rel.target_entity_id == entity_id:
                if rel.source_entity_id not in seen:
                    seen.add(rel.source_entity_id)
                    neighbors.append(rel.source_entity_id)
        return neighbors

    def traverse_bfs(
        self,
        start_entity_id: str,
        max_depth: int,
        *,
        relationship_type: str | None = None,
    ) -> list[GraphTraversalNode]:
        if start_entity_id not in self._entities:
            raise GraphEntityNotFoundError(f"entity not found: {start_entity_id}")
        if max_depth < 0:
            return []

        visited: set[str] = {start_entity_id}
        result: list[GraphTraversalNode] = [
            GraphTraversalNode(entity_id=start_entity_id, depth=0)
        ]
        queue: deque[tuple[str, int]] = deque([(start_entity_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor_id in self.get_neighbors(
                current_id,
                relationship_type=relationship_type,
                outgoing=True,
                incoming=False,
            ):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                next_depth = depth + 1
                result.append(
                    GraphTraversalNode(entity_id=neighbor_id, depth=next_depth)
                )
                queue.append((neighbor_id, next_depth))

        return result
