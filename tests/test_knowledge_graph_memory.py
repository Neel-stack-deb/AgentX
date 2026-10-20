import pytest

from Memory.exceptions import GraphEntityNotFoundError
from Memory.knowledge_graph import InMemoryKnowledgeGraphStore
from Types.KnowledgeGraph import GraphEntity, GraphRelationship


def _entity(entity_id: str, name: str, **props: str) -> GraphEntity:
    return GraphEntity(entity_id=entity_id, name=name, properties=dict(props))


@pytest.fixture
def graph() -> InMemoryKnowledgeGraphStore:
    return InMemoryKnowledgeGraphStore()


def test_entity_upsert_and_get(graph: InMemoryKnowledgeGraphStore):
    graph.upsert_entity(_entity("agentx", "AgentX"))
    loaded = graph.get_entity("agentx")
    assert loaded is not None
    assert loaded.name == "AgentX"


def test_relationship_requires_existing_entities(graph: InMemoryKnowledgeGraphStore):
    graph.upsert_entity(_entity("agentx", "AgentX"))
    with pytest.raises(GraphEntityNotFoundError):
        graph.add_relationship(
            GraphRelationship(
                source_entity_id="agentx",
                target_entity_id="postgres",
                relationship_type="USES",
            )
        )


def test_neighbors_and_typed_relationships(graph: InMemoryKnowledgeGraphStore):
    graph.upsert_entity(_entity("agentx", "AgentX"))
    graph.upsert_entity(_entity("postgres", "PostgreSQL"))
    graph.upsert_entity(_entity("retriever", "MemoryRetriever"))
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="postgres",
            relationship_type="USES",
            source_memory_ids=["mem-1"],
        )
    )
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="retriever",
            relationship_type="USES",
        )
    )

    all_neighbors = graph.get_neighbors("agentx")
    assert set(all_neighbors) == {"postgres", "retriever"}

    storage_neighbors = graph.get_neighbors("agentx", relationship_type="USES")
    assert set(storage_neighbors) == {"postgres", "retriever"}

    graph.add_relationship(
        GraphRelationship(
            source_entity_id="retriever",
            target_entity_id="postgres",
            relationship_type="QUERIES",
        )
    )
    queries_only = graph.get_neighbors("retriever", relationship_type="QUERIES")
    assert queries_only == ["postgres"]


def test_bfs_respects_max_depth(graph: InMemoryKnowledgeGraphStore):
    for eid in ("a", "b", "c", "d"):
        graph.upsert_entity(_entity(eid, eid))
    graph.add_relationship(
        GraphRelationship(source_entity_id="a", target_entity_id="b", relationship_type="LINK")
    )
    graph.add_relationship(
        GraphRelationship(source_entity_id="b", target_entity_id="c", relationship_type="LINK")
    )
    graph.add_relationship(
        GraphRelationship(source_entity_id="c", target_entity_id="d", relationship_type="LINK")
    )

    depth_2 = graph.traverse_bfs("a", max_depth=2)
    ids = [node.entity_id for node in depth_2]
    assert ids == ["a", "b", "c"]

    depth_0 = graph.traverse_bfs("a", max_depth=0)
    assert [n.entity_id for n in depth_0] == ["a"]


def test_bfs_handles_cycles_without_infinite_loop(graph: InMemoryKnowledgeGraphStore):
    graph.upsert_entity(_entity("x", "X"))
    graph.upsert_entity(_entity("y", "Y"))
    graph.add_relationship(
        GraphRelationship(source_entity_id="x", target_entity_id="y", relationship_type="LINK")
    )
    graph.add_relationship(
        GraphRelationship(source_entity_id="y", target_entity_id="x", relationship_type="LINK")
    )

    visited = graph.traverse_bfs("x", max_depth=10)
    assert len(visited) == 2
    assert {n.entity_id for n in visited} == {"x", "y"}


def test_bfs_filters_by_relationship_type(graph: InMemoryKnowledgeGraphStore):
    graph.upsert_entity(_entity("agentx", "AgentX"))
    graph.upsert_entity(_entity("postgres", "PostgreSQL"))
    graph.upsert_entity(_entity("retriever", "MemoryRetriever"))
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx", target_entity_id="postgres", relationship_type="USES"
        )
    )
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="agentx",
            target_entity_id="retriever",
            relationship_type="CONTAINS",
        )
    )
    graph.add_relationship(
        GraphRelationship(
            source_entity_id="retriever",
            target_entity_id="postgres",
            relationship_type="QUERIES",
        )
    )

    uses_only = graph.traverse_bfs("agentx", max_depth=3, relationship_type="USES")
    assert [n.entity_id for n in uses_only] == ["agentx", "postgres"]


def test_missing_entity_on_neighbors_and_traverse(graph: InMemoryKnowledgeGraphStore):
    with pytest.raises(GraphEntityNotFoundError):
        graph.get_neighbors("missing")
    with pytest.raises(GraphEntityNotFoundError):
        graph.traverse_bfs("missing", max_depth=1)
