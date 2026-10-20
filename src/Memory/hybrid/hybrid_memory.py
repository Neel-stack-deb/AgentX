"""Hybrid memory: vector retrieval augmented with knowledge-graph traversal."""

from __future__ import annotations

from Memory.knowledge_graph.knowledge_graph_store import KnowledgeGraphStore
from Memory.memory_retriever import MemoryRetriever
from Memory.retrieval import MemoryRetrievalFilter
from Types.HybridMemory import HybridMemoryResult
from Types.KnowledgeGraph import GraphEntity, GraphTraversalNode


class HybridMemoryRetriever:
    """
    Combines semantic memory search with explicit graph links.

    Entity seeds come from `source_memory_ids` on graph nodes/edges — no LLM extraction.
    """

    def __init__(
        self,
        memory_retriever: MemoryRetriever,
        knowledge_graph: KnowledgeGraphStore,
    ) -> None:
        self._memory_retriever = memory_retriever
        self._graph = knowledge_graph

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: MemoryRetrievalFilter | None = None,
        graph_max_depth: int = 2,
        relationship_type: str | None = None,
    ) -> HybridMemoryResult:
        scored = self._memory_retriever.retrieve(
            query=query, top_k=top_k, filters=filters
        )
        memories = [item.memory for item in scored]
        memory_ids: list[str] = []
        seen_memory: set[str] = set()
        for memory in memories:
            if memory.memory_id in seen_memory:
                continue
            seen_memory.add(memory.memory_id)
            memory_ids.append(memory.memory_id)

        seed_entity_ids: set[str] = set()
        for mid in memory_ids:
            seed_entity_ids.update(self._graph.find_entity_ids_for_memory(mid))

        traversal: list[GraphTraversalNode] = []
        visited_traversal: set[tuple[str, int]] = set()
        entity_ids_in_scope: set[str] = set()
        for seed_id in sorted(seed_entity_ids):
            for node in self._graph.traverse_bfs(
                seed_id,
                graph_max_depth,
                relationship_type=relationship_type,
            ):
                key = (node.entity_id, node.depth)
                if key in visited_traversal:
                    continue
                visited_traversal.add(key)
                traversal.append(node)
                entity_ids_in_scope.add(node.entity_id)

        entities: list[GraphEntity] = []
        for eid in sorted(entity_ids_in_scope):
            entity = self._graph.get_entity(eid)
            if entity is not None:
                entities.append(entity)

        relationships = self._graph.relationships_between(
            entity_ids_in_scope, relationship_type=relationship_type
        )

        return HybridMemoryResult(
            query=query,
            memories=memories,
            memory_ids=memory_ids,
            entities=entities,
            relationships=relationships,
            graph_traversal=traversal,
        )
