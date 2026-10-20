# Hybrid Memory in AgentX

**Hybrid memory** combines different *representations* of memory (vector text recall + explicit graph structure). It is not hybrid *search* (e.g. BM25 + vectors).

## 1. Concept

Many questions need both:

- **Similarity:** “What did we write about PostgreSQL?” → vector retrieval over `Memory.content`.
- **Structure:** “What does AgentX use?” → typed edges in the knowledge graph.

Hybrid retrieval runs vector search first, then uses **explicit links** (`source_memory_ids` on entities and relationships) to seed graph traversal.

## 2. Architecture

| Component | Role |
|-----------|------|
| `MemoryRetriever` / `VectorMemoryRetriever` | Semantic candidate memories |
| `KnowledgeGraphStore` | Entities, edges, BFS |
| `HybridMemoryRetriever` | Orchestrates both into `HybridMemoryResult` |
| `Types/HybridMemory.py` | Result model (memories, entities, relationships, traversal trace) |

```
Query
  → VectorMemoryRetriever (top_k)
  → memory_ids (deduped, stable order)
  → find_entity_ids_for_memory (per id)
  → traverse_bfs from each seed (max_depth, optional rel type)
  → HybridMemoryResult
```

No LLM entity extraction: if a memory is not referenced in `source_memory_ids`, it still appears in `memories` but does not seed the graph.

## 3. Data flow

1. Embed query and retrieve scored memories (existing eligibility/ranking).
2. Collect unique `memory_id` values in retrieval order.
3. For each id, collect graph entity seeds via `find_entity_ids_for_memory`.
4. BFS from each seed (sorted for determinism); merge traversal nodes without duplicate `(entity_id, depth)` pairs.
5. Hydrate entities; include relationships whose endpoints are both in scope.
6. Return bounded payload — not injected into prompts automatically.

## 4. Design decisions

- **Deterministic ordering:** sorted entity seeds, sorted relationship ids, deduped memory ids.
- **Separate from `MemoryManager`:** constructed with a retriever + graph store; integration milestone wires optional helpers on `MemoryManager`.
- **Depth and rel-type filters** mirror graph store capabilities.

## 5. Example

```python
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.hybrid import HybridMemoryRetriever
from Memory.knowledge_graph import InMemoryKnowledgeGraphStore
from Memory.memory_manager import MemoryManager

manager = MemoryManager(embedding_provider=HashEmbeddingProvider())
graph = InMemoryKnowledgeGraphStore()
# ... remember content, link entity.source_memory_ids = [memory.memory_id]

hybrid = HybridMemoryRetriever(memory_retriever=manager._retriever, knowledge_graph=graph)
result = hybrid.retrieve("Why PostgreSQL?", top_k=5, graph_max_depth=2)
```

## 6. Tests

```bash
pytest tests/test_hybrid_memory.py -q
```

## 7. Limitations

- Seeds only from explicit `source_memory_ids` (no NER).
- Graph expansion is outgoing BFS only (same as graph store default).
- Not yet called from `Orchestrator` (integration milestone).
- Does not rank graph entities by relevance beyond vector-selected seeds.

Future: optional `memory_id → entity_id` registry, incoming-edge traversal, prompt-sized summarization of `HybridMemoryResult`.
