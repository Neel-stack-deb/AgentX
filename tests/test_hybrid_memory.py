from Memory.embedding_provider import HashEmbeddingProvider
from Memory.hybrid import HybridMemoryRetriever
from Memory.knowledge_graph import InMemoryKnowledgeGraphStore
from Memory.memory_manager import MemoryManager
from Types.KnowledgeGraph import GraphEntity, GraphRelationship


def _wire_agentx_graph(graph: InMemoryKnowledgeGraphStore) -> None:
    graph.upsert_entity(GraphEntity(entity_id="agentx", name="AgentX"))
    graph.upsert_entity(GraphEntity(entity_id="postgres", name="PostgreSQL"))
    graph.upsert_entity(GraphEntity(entity_id="retriever", name="MemoryRetriever"))
    graph.upsert_entity(GraphEntity(entity_id="pgvector", name="PgVectorStore"))
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="postgres",
            relationship_type="USES",
        )
    )
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="retriever",
            target_entity_id="pgvector",
            relationship_type="QUERIES",
        )
    )


def test_hybrid_combines_vector_and_graph_without_duplicate_memories():
    provider = HashEmbeddingProvider(dimensions=32)
    manager = MemoryManager(embedding_provider=provider)
    graph = InMemoryKnowledgeGraphStore()
    _wire_agentx_graph(graph)

    decision = manager.remember(
        "AgentX chose PostgreSQL for durable memory and pgvector for similarity search.",
        source="architecture-decision",
    )
    graph.upsert_entity(
        GraphEntity(
            entity_id="agentx",
            name="AgentX",
            source_memory_ids=[decision.memory_id],
        )
    )
    graph.upsert_entity(GraphEntity(entity_id="postgres", name="PostgreSQL"))
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="postgres",
            relationship_type="USES",
            source_memory_ids=[decision.memory_id],
        )
    )

    hybrid = HybridMemoryRetriever(
        memory_retriever=manager._retriever,
        knowledge_graph=graph,
    )
    result = hybrid.retrieve(
        "Why did AgentX choose PostgreSQL for memory?",
        top_k=3,
        graph_max_depth=2,
    )

    assert len(result.memory_ids) == len(set(result.memory_ids))
    assert decision.memory_id in result.memory_ids
    assert any(e.entity_id == "postgres" for e in result.entities)
    assert any(r.relationship_type == "USES" for r in result.relationships)


def test_hybrid_graph_expansion_follows_bfs_depth():
    provider = HashEmbeddingProvider(dimensions=32)
    manager = MemoryManager(embedding_provider=provider)
    graph = InMemoryKnowledgeGraphStore()
    _wire_agentx_graph(graph)

    mem = manager.remember("MemoryRetriever queries PgVectorStore for candidates.")
    graph.upsert_entity(
        GraphEntity(
            entity_id="retriever",
            name="MemoryRetriever",
            source_memory_ids=[mem.memory_id],
        )
    )

    hybrid = HybridMemoryRetriever(
        memory_retriever=manager._retriever,
        knowledge_graph=graph,
    )
    shallow = hybrid.retrieve(
        "MemoryRetriever vector queries",
        top_k=1,
        graph_max_depth=0,
    )
    deep = hybrid.retrieve(
        "MemoryRetriever vector queries",
        top_k=1,
        graph_max_depth=2,
        relationship_type="QUERIES",
    )

    shallow_ids = {e.entity_id for e in shallow.entities}
    deep_ids = {e.entity_id for e in deep.entities}
    assert shallow_ids == {"retriever"}
    assert "pgvector" in deep_ids


def test_hybrid_returns_vector_memories_without_graph_links():
    provider = HashEmbeddingProvider(dimensions=32)
    manager = MemoryManager(embedding_provider=provider)
    graph = InMemoryKnowledgeGraphStore()

    orphan = manager.remember("Standalone fact with no graph linkage.")
    hybrid = HybridMemoryRetriever(
        memory_retriever=manager._retriever,
        knowledge_graph=graph,
    )
    result = hybrid.retrieve("Standalone fact", top_k=3)

    assert result.memory_ids == [orphan.memory_id]
    assert result.entities == []
    assert result.relationships == []
