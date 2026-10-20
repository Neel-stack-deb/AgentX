import pytest

from Memory.embedding_provider import HashEmbeddingProvider
from Memory.hierarchical import InMemoryHierarchicalSummaryStore
from Memory.knowledge_graph import InMemoryKnowledgeGraphStore
from Memory.memory_manager import MemoryManager
from Types.HierarchicalMemory import (
    HierarchicalRetrievalIntent,
    MemorySummary,
    SummaryScopeType,
)
from Types.KnowledgeGraph import GraphEntity, GraphRelationship


def test_memory_manager_retrieve_hybrid_requires_graph():
    manager = MemoryManager(embedding_provider=HashEmbeddingProvider(dimensions=32))
    with pytest.raises(RuntimeError, match="knowledge_graph"):
        manager.retrieve_hybrid("query")


def test_memory_manager_retrieve_hierarchical_requires_summary_store():
    manager = MemoryManager(embedding_provider=HashEmbeddingProvider(dimensions=32))
    with pytest.raises(RuntimeError, match="summary_store"):
        manager.retrieve_hierarchical(
            HierarchicalRetrievalIntent.OVERVIEW,
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
        )


def test_memory_manager_expanded_retrieval_paths():
    provider = HashEmbeddingProvider(dimensions=32)
    graph = InMemoryKnowledgeGraphStore()
    summaries = InMemoryHierarchicalSummaryStore()
    manager = MemoryManager(
        embedding_provider=provider,
        knowledge_graph=graph,
        summary_store=summaries,
    )

    memory = manager.remember("AgentX uses PostgreSQL for memory persistence.")
    graph.upsert_entity(
        GraphEntity(
            entity_id="agentx",
            name="AgentX",
            source_memory_ids=[memory.memory_id],
        )
    )
    graph.upsert_entity(GraphEntity(entity_id="postgres", name="PostgreSQL"))
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="postgres",
            relationship_type="USES",
        )
    )
    summaries.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="High-level AgentX overview.",
            source_memory_ids=[memory.memory_id],
        )
    )

    hybrid = manager.retrieve_hybrid("PostgreSQL memory", top_k=3)
    assert memory.memory_id in hybrid.memory_ids
    assert any(e.entity_id == "postgres" for e in hybrid.entities)

    overview = manager.retrieve_hierarchical(
        HierarchicalRetrievalIntent.OVERVIEW,
        scope_type=SummaryScopeType.GLOBAL,
        scope_id="agentx",
    )
    assert overview.summary is not None
    assert not overview.insufficient_evidence

    detail = manager.retrieve_hierarchical(
        HierarchicalRetrievalIntent.DETAIL,
        scope_type=SummaryScopeType.GLOBAL,
        scope_id="agentx",
    )
    assert len(detail.detailed_memories) == 1


def test_vector_retrieve_remains_backward_compatible():
    manager = MemoryManager(embedding_provider=HashEmbeddingProvider(dimensions=32))
    memory = manager.remember("backward compatible vector path")
    results = manager.retrieve("backward compatible", top_k=1)
    assert results[0].memory_id == memory.memory_id
