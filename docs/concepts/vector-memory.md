# Vector Memory in AgentX

This document describes how AgentX adds **long-term vector memory** without changing who owns execution flow or how LLM prompts are built.

## 1. What vector memory is

Vector memory stores text as **embedding vectors** (lists of numbers) so we can find past information that is *semantically similar* to a new query, even when the wording differs.

## 2. Why AgentX needs it

`ExecutionContext` holds **current-run state**. `History` holds an **append-only audit** of what happened in a run. Neither is designed for cross-run recall. Vector memory fills that gap: durable facts, preferences, and outcomes the agent should reuse later.

## 3. How embeddings work

An **embedding model** maps text → a fixed-size vector. Similar meanings tend to land closer in that space. AgentX never hard-codes a vendor API here; it depends on `EmbeddingProvider`.

## 4. How vector similarity works

Retrieval compares the **query embedding** to **stored embeddings** and ranks neighbors. We use **cosine similarity**: measure the angle between two vectors (not their length). Values near `1.0` mean very aligned direction; near `0` means unrelated.

## 5. Cosine similarity (conceptual)

Think of each embedding as an arrow. Cosine similarity asks: “Are these arrows pointing the same way?” It ignores magnitude when vectors are normalized, which stabilizes comparison across short and long texts.

## 6. VectorStore responsibility

`VectorStore` only:

- upsert `VectorIndexRecord` (embedding + denormalized `VectorIndexMetadata`)
- delete by `memory_id`
- `similarity_search(query_embedding, top_k, filters?)`

It exposes `search_strategy` (`brute_force` vs `ann`) so operators know what they are running. AgentX code never branches on that flag.

It does **not** know about goals, plans, nodes, or prompts. Swap `BruteForceVectorStore` / `InMemoryVectorStore` for pgvector, Qdrant, Chroma, or an ANN library by implementing the same interface.

### Why VectorStore is an abstraction

Production teams change storage often (managed DB, self-hosted ANN, multi-tenant indexes). If retrieval logic leaked into `MemoryManager` or the Orchestrator, every migration would touch execution flow. The interface keeps **similarity search + optional metadata filters** behind one seam.

## 7. EmbeddingProvider responsibility

`EmbeddingProvider` embeds text (single or batch) and exposes:

- `model_name` — logical embedding model id  
- `model_version` — version string for migration  
- `dimensions` — vector width  

It does **not** persist memories or call the LLM. Production: implement a thin adapter around OpenAI, Cohere, local sentence-transformers, etc.

**Development default:** `HashEmbeddingProvider` (`hash-bow`, version `1`) — deterministic token hashing, no API keys.

### Embedding versioning and migration (future)

```
Embedding Model V1  →  vectors in index tagged embedding_version=V1
        ↓
Embedding Model V2  →  new writes use V2; old vectors are incompatible
        ↓
Re-embedding job   →  read Memory.content, re-embed with V2, upsert index
```

AgentX stores `embedding_model`, `embedding_version`, and `embedding_dimension` on each `Memory` and on `VectorIndexMetadata`. Retrieval can filter by model/version so mixed indexes are safe during rollout. A full migration pipeline is **not** implemented yet.

## 8. MemoryRetriever responsibility

Retrieval contract (unchanged conceptually):

```
Query → EmbeddingProvider → VectorStore (candidates) → MemoryRetriever → ScoredMemory
```

`VectorMemoryRetriever`:

1. embed query  
2. pass optional `MemoryRetrievalFilter` to `VectorStore`  
3. hydrate `Memory` from `MemoryStore`  
4. enforce `ACTIVE` status and superseded exclusion  

**Vector similarity is candidate generation, not final relevance.** No reranker or cross-encoder in this module.

### Metadata filtering

`MemoryRetrievalFilter` supports optional `memory_type`, `status`, `project_id`, `scope`, `embedding_model`, `embedding_version`, and `exclude_superseded`. Filters are applied inside `VectorStore` against `VectorIndexMetadata` (reducing search space before scoring in brute-force mode). The Orchestrator does not construct filters; callers of `MemoryManager.retrieve(..., filters=...)` do.

## 9. MemoryManager responsibility

`MemoryManager` is the **framework-facing API**:

| Method | Behavior |
|--------|----------|
| `remember(content, …)` | Create `Memory`, embed, persist record + vector index metadata |
| `retrieve(query, top_k, filters?)` | Return `Memory` list (scores via `retrieve_scored`) |
| `supersede(old_id, new_id)` | Mark stale memory; excluded from default retrieval |
| `update` / `touch_content` | Update record and re-embed |
| `delete` | Soft-delete in store + remove from vector index |

It coordinates components but **does not** run the planner loop or format LLM messages.

## 10. Orchestrator integration

Before planning, when a `MemoryManager` is injected:

```
Goal → Orchestrator → MemoryManager.retrieve(goal.description)
     → ExecutionContextManager.with_retrieved_memories(...)
     → Planner / Executor / Reflector (unchanged control flow)
```

`MemoryManager` is optional (`None` preserves previous behavior).

## 11. Retrieved memory in ExecutionContext

`ExecutionContext.retrieved_memories: list[Memory]` is populated only via `ExecutionContextManager.with_retrieved_memories`, which uses `model_copy` — **no in-place mutation**.

Nodes read context; they do not write memory.

## 12. History vs memory

| | History | Memory |
|---|---------|--------|
| Scope | Single execution | Cross-run |
| Mutability | Append-only log | CRUD + vector index |
| Content | Events + artifacts | Searchable `Memory.content` |
| Used for | Trace/debug/replay | Semantic recall |

Do not append memories into `History` or mirror history rows into the vector store automatically (not in v1).

## 13. Prompt path

```
Memory → ExecutionContext.retrieved_memories → PromptBuilder → LLM
```

`PromptBuilder._format_retrieved_memories` adds a “Relevant memories” block to the **planner** template only (v1). MemoryManager never builds prompts.

## 14. Memory domain schema

`Types.Memory.Memory`:

- `memory_id` — UUID string, vector key  
- `content` — searchable text  
- `memory_type` — `episodic` \| `semantic` \| `procedural`  
- `created_at` / `updated_at` — UTC timestamps  
- `source` — optional provenance (e.g. execution id)  
- `importance` — optional 0..1 (reserved for future ranking)  
- `status` — `active` \| `archived` \| `deleted` (delete is soft in `MemoryStore`)  
- `project_id` / `scope` — optional partition for filters  
- `embedding_model` / `embedding_version` / `embedding_dimension` — index compatibility  
- `superseded_by_memory_id` — stale lineage; default retrieval skips these  

`ScoredMemory` pairs `Memory` with retrieval score.

### Stale memory (current vs future)

- **Today:** `MemoryManager.supersede()` sets `superseded_by_memory_id` and refreshes the vector index metadata. Retriever excludes superseded rows when `exclude_superseded=True`.  
- **Future:** TTL policies, automatic archival, compression, and conflict resolution stay in `MemoryManager` / `MemoryStore` — not in `History` or nodes.

---

## 15. Search algorithms — concepts

### Brute-force search (current default)

`BruteForceVectorStore` compares the query vector to **every** indexed vector (after metadata filter). Cost is approximately **O(N × D)** for N vectors and dimension D. Correct for exact cosine ranking over the filtered set; fine for dev and small corpora.

### Approximate Nearest Neighbor (ANN) — future production

At large N, full scan is too slow. ANN indexes (e.g. **HNSW**, **IVF**) trade **recall** for **latency**: they may miss the true nearest neighbors but return good candidates fast. AgentX does **not** ship HNSW or IVF today; a production `VectorStore` with `search_strategy=ann` would hide that choice.

| Approach | Idea | AgentX today |
|----------|------|----------------|
| Brute force | Scan all vectors | **Yes** (`BruteForceVectorStore`) |
| HNSW | Graph-based greedy search on a small-world graph | No — implement behind `VectorStore` |
| IVF | Cluster centroids, search top clusters only | No — implement behind `VectorStore` |

**Where ANN belongs:** only inside a `VectorStore` implementation. `MemoryRetriever` and `MemoryManager` stay identical.

### Recall vs latency

Stricter ANN parameters → faster queries, lower recall. Tuning is an ops concern for the chosen backend, not the Orchestrator.

---

## 16. CURRENT IMPLEMENTATION

```
src/Memory/
  embedding_provider.py   # EmbeddingProvider + HashEmbeddingProvider (model_name/version)
  retrieval.py            # MemoryRetrievalFilter, VectorIndexRecord, metadata helpers
  vector_math.py          # cosine_similarity
  vector_store.py         # VectorStore, BruteForceVectorStore, InMemoryVectorStore
  memory_store.py         # MemoryStore + InMemoryMemoryStore (in-process records)
  memory_retriever.py     # VectorMemoryRetriever
  memory_manager.py       # MemoryManager
src/Types/Memory.py       # domain models
```

- **Persistence:** `InMemoryMemoryStore` holds `Memory` records; `BruteForceVectorStore` holds vectors + index metadata. Nothing is durable across process restarts.  
- **Vector search:** brute-force cosine over in-memory records with optional metadata pre-filter.  
- **ANN:** not implemented; `VectorSearchStrategy.ANN` reserved for future backends.

Optional benchmark (not CI): `tests/benchmarks/test_bruteforce_vector_bench.py` with `AGENTX_RUN_BENCH=1`.

## 17. FUTURE PRODUCTION DESIGN

1. Durable `MemoryStore` (SQL/document).  
2. `VectorStore` backed by pgvector / Qdrant / etc., or ANN library isolated behind `VectorStore`.  
3. Re-embedding worker when `embedding_version` changes.  
4. Optional reranker **after** vector candidates (not part of vector memory v1).  
5. Orchestrator and nodes unchanged.

## 18. Current limitations

- In-memory only; no persistence across process restarts  
- Hash embeddings are not semantically strong  
- Brute-force search only (no HNSW/IVF in repo)  
- No hybrid / graph memory, no reranking, no automatic “remember after run” hook  
- Planner prompt only (executor/reflector templates unchanged)  
- No full embedding migration pipeline  

## 19. Replacing the vector backend

1. Implement `VectorStore` (upsert `VectorIndexRecord`, filtered `similarity_search`).  
2. Set `search_strategy` to `ann` when using an approximate index.  
3. Optionally implement durable `MemoryStore`.  
4. Inject both into `MemoryManager`.  
5. **Orchestrator and ExecutionContextManager stay unchanged.**

## 20. Architectural decisions

- **MemoryManager optional on Orchestrator** — avoids breaking callers without memory.  
- **Split MemoryStore vs VectorStore** — metadata CRUD vs similarity index (matches how production DBs are often split).  
- **Context evolution via ContextManager** — retrieved memories follow ADR-001/005, same as node results.  
- **HashEmbeddingProvider for dev** — keeps CI/local free of secrets while preserving swap-friendly `EmbeddingProvider`.  
- **Soft delete** — preserves audit-friendly metadata while excluding deleted rows from retrieval.  
- **Denormalized `VectorIndexMetadata`** — enables filter-before-score without joining stores on every brute-force scan.  
- **Embedding tags on Memory** — enables safe mixed-version indexes during model upgrades.  
- **Supersede on MemoryManager** — stale handling stays out of nodes and History.
