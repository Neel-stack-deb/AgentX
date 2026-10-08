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

- upsert `(memory_id → embedding)`
- delete by `memory_id`
- `similarity_search(query_embedding, top_k)`

It does **not** know about goals, plans, nodes, or prompts. Swap `InMemoryVectorStore` for pgvector/Qdrant/Chroma by implementing the same interface.

## 7. EmbeddingProvider responsibility

`EmbeddingProvider` only embeds text (single or batch). It does **not** persist memories or call the LLM. Production: implement a thin adapter around OpenAI, Cohere, local sentence-transformers, etc.

**Development default:** `HashEmbeddingProvider` — deterministic token hashing, no API keys, good enough for tests and local wiring.

## 8. MemoryRetriever responsibility

`VectorMemoryRetriever`:

1. embed query  
2. ask `VectorStore` for top-K `(memory_id, score)`  
3. hydrate `Memory` from `MemoryStore`  
4. drop non-`ACTIVE` records  

Ranking is pure vector score today (no reranker).

## 9. MemoryManager responsibility

`MemoryManager` is the **framework-facing API**:

| Method | Behavior |
|--------|----------|
| `remember(content, …)` | Create `Memory`, embed, persist record + vector |
| `retrieve(query, top_k)` | Return `Memory` list (scores via `retrieve_scored`) |
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

`ScoredMemory` pairs `Memory` with retrieval score.

## 15. Current implementation

```
src/Memory/
  embedding_provider.py   # EmbeddingProvider + HashEmbeddingProvider
  vector_math.py          # cosine_similarity
  vector_store.py         # VectorStore + InMemoryVectorStore
  memory_store.py         # MemoryStore + InMemoryMemoryStore
  memory_retriever.py     # VectorMemoryRetriever
  memory_manager.py       # MemoryManager
src/Types/Memory.py       # domain models
```

## 16. Current limitations

- In-memory only; no persistence across process restarts  
- Hash embeddings are not semantically strong  
- No hybrid / graph memory, no reranking, no automatic “remember after run” hook  
- Planner prompt only (executor/reflector templates unchanged)  
- No memory-type or metadata filters on retrieve  

## 17. Replacing the vector backend

1. Implement `VectorStore` against your database (store `memory_id`, float array, optional index).  
2. Optionally implement `MemoryStore` for durable metadata.  
3. Inject both into `MemoryManager`.  
4. **Orchestrator and ExecutionContextManager stay unchanged.**

## 18. Architectural decisions

- **MemoryManager optional on Orchestrator** — avoids breaking callers without memory.  
- **Split MemoryStore vs VectorStore** — metadata CRUD vs similarity index (matches how production DBs are often split).  
- **Context evolution via ContextManager** — retrieved memories follow ADR-001/005, same as node results.  
- **HashEmbeddingProvider for dev** — keeps CI/local free of secrets while preserving swap-friendly `EmbeddingProvider`.  
- **Soft delete** — preserves audit-friendly metadata while excluding deleted rows from retrieval.
