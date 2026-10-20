# Knowledge Graph Memory in AgentX

Educational implementation of **entity–relationship memory** alongside vector memory. It does not replace `MemoryStore` or `VectorStore`.

## 1. Concept (first principles)

Vector memory answers: *“What text is semantically similar to this query?”*

A **knowledge graph** answers: *“What is explicitly connected to what, and how?”*

Nodes are **entities** (e.g. `AgentX`, `PostgreSQL`). Edges are **typed relationships** (e.g. `USES`, `QUERIES`). Properties and `source_memory_ids` attach metadata and provenance without duplicating full memory text in the graph.

## 2. Architecture in AgentX

| Piece | Role |
|-------|------|
| `Types/KnowledgeGraph.py` | `GraphEntity`, `GraphRelationship`, `GraphTraversalNode` |
| `KnowledgeGraphStore` | Abstract store API |
| `InMemoryKnowledgeGraphStore` | Default in-process adjacency list |

The graph is **separate** from `MemoryManager` in v1 of this milestone: callers link entities to vector memories via `source_memory_ids` on entities and relationships.

```
Explicit API / tests
        │
        ▼
InMemoryKnowledgeGraphStore
        ├─ entities: dict[entity_id → GraphEntity]
        └─ relationships: list[GraphRelationship] (adjacency via scan)
```

No graph database and no PostgreSQL tables yet—persistence would reuse patterns from `PostgresMemoryRepository` later if needed.

## 3. Data flow

1. **Write:** `upsert_entity` → optional `add_relationship` (both endpoints must exist).
2. **Local query:** `get_neighbors(entity_id, relationship_type=...)`.
3. **Multi-hop:** `traverse_bfs(start, max_depth, relationship_type=...)` — BFS with a visited set so cycles cannot loop forever.

Traversal is **outgoing** only (follows `source → target`). Incoming edges can be read with `get_neighbors(..., incoming=True)`.

## 4. Design decisions

- **In-memory first:** smallest surface for learning and unit tests without Docker.
- **Directed typed edges:** matches architecture diagrams (`MemoryRetriever --QUERIES--> PgVectorStore`).
- **Fail fast:** missing entities raise `GraphEntityNotFoundError` (subclass of `MemoryStoreError`).
- **No automatic extraction:** entities are created explicitly; hybrid memory (next milestone) will combine with vector hits using metadata.

## 5. Example

```python
from Memory.knowledge_graph import InMemoryKnowledgeGraphStore
from Types.KnowledgeGraph import GraphEntity, GraphRelationship

g = InMemoryKnowledgeGraphStore()
g.upsert_entity(GraphEntity(entity_id="agentx", name="AgentX"))
g.upsert_entity(GraphEntity(entity_id="postgres", name="PostgreSQL"))
g.add_relationship(
    GraphRelationship(
        source_entity_id="agentx",
        target_entity_id="postgres",
        relationship_type="USES",
        source_memory_ids=["<memory-uuid>"],
    )
)
g.traverse_bfs("agentx", max_depth=2)
```

## 6. Run tests

From the repo root (no database required):

```bash
pytest tests/test_knowledge_graph_memory.py -q
```

Full suite: `pytest` (existing vector/orchestrator tests should still pass).

## 7. Limitations and extensions

- No persistence across process restarts.
- Neighbor lookup scans all relationships (fine for POC scale).
- Not wired into `Orchestrator` or `MemoryManager` yet (integration milestone).
- Possible future work: SQL tables for entities/edges, bidirectional traversal helpers, sync from `Memory.metadata` when a standard schema exists.
