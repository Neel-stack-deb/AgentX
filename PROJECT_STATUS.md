# AgentX Project Status

## Version

**0.2.1-dev** — Module 2 vector memory foundation + production-readiness pass.

## Module 1 — Core agent loop (existing)

| Component | Status | Notes |
|-----------|--------|-------|
| Orchestrator | Implemented | Owns planner → executor ↔ reflector loop |
| RuntimeContext | Implemented | Mutable run metadata (`execution_id`, status, current node) |
| ExecutionContext | Implemented | Immutable pydantic state per ADR-001 |
| ExecutionContextManager | Implemented | Applies node results; adds `with_retrieved_memories` |
| History | Implemented | Append-only events + artifacts |
| Nodes (Planner, Executer, Reflector) | Implemented | Return results only; no mutual calls |
| NodeRunner | Implemented | History + context evolution |
| PromptBuilder | Implemented | Planner template includes retrieved memories when present |
| LLM (BaseLLMClient, MockLLMClient) | Partial | Mock client for development |
| Artifacts & Events | Implemented | Structured domain records |
| Scratchpad | Implemented | On ExecutionContext |
| ADRs 001–005 | Documented | Under `src/Docs/ADR/` |

## Module 2 — Agent Memory

| Component | Status | Notes |
|-----------|--------|-------|
| Memory domain (`Types/Memory.py`) | **Done (v1.1)** | + embedding tags, `project_id`/`scope`, supersede field |
| EmbeddingProvider | **Done (v1.1)** | `model_name` / `model_version` + `HashEmbeddingProvider` |
| VectorStore | **Done (v1.1)** | `BruteForceVectorStore`, filters, `VectorSearchStrategy` |
| MemoryStore | **Done (v1)** | ABC + `InMemoryMemoryStore`, soft delete |
| MemoryRetriever | **Done (v1.1)** | `MemoryRetrievalFilter` on retrieve |
| MemoryManager | **Done (v1.1)** | + `supersede`, filtered retrieve |
| Retrieval contracts | **Done (v1.1)** | `Memory/retrieval.py` |
| ANN (HNSW / IVF) | Not implemented | Future `VectorStore` backends only |
| Orchestrator integration | **Done (v1)** | Optional retrieve before planning |
| Knowledge graph memory | Not started | Out of scope for this milestone |
| Hybrid memory | Not started | Out of scope |
| Advanced ranking | Not started | Vector score only |

## Vector memory — current behavior

- **Foundation (v1):** Orchestrator optional retrieve → `with_retrieved_memories` → planner prompt.
- **Retrieval (v1.1):** Brute-force cosine **O(N×D)** over in-memory `VectorIndexRecord` entries; optional `MemoryRetrievalFilter` (`project_id`, `scope`, `memory_type`, `status`, embedding model/version).
- **ANN readiness:** New backends implement `VectorStore` only; declare `search_strategy=ann` when approximate. No HNSW/IVF in tree.
- **Embedding versioning:** Stored on each `Memory` and index metadata; filter by version during mixed rollouts; no re-embed worker yet.
- **Stale memories:** `MemoryManager.supersede()` + `superseded_by_memory_id`; excluded from default retrieval.

See [docs/concepts/vector-memory.md](docs/concepts/vector-memory.md).

## New files (Module 2)

- `src/Types/Memory.py`
- `src/Memory/embedding_provider.py`
- `src/Memory/vector_math.py`
- `src/Memory/vector_store.py`
- `src/Memory/memory_store.py`
- `src/Memory/memory_retriever.py`
- `src/Memory/memory_manager.py`
- `src/Memory/retrieval.py`
- `tests/benchmarks/test_bruteforce_vector_bench.py` (optional, `AGENTX_RUN_BENCH=1`)
- `docs/concepts/vector-memory.md`
- `tests/test_vector_memory.py`
- `tests/test_orchestrator_memory.py`
- `pytest.ini`
- `src/Types/__init__.py`, `src/Memory/__init__.py`, `src/llm/__init__.py` (minimal packages; `Core/__init__.py` kept empty to avoid import cycles)

## Modified files (Module 2 + minimal wiring fixes)

- `src/Core/ExecutionContext.py` — `retrieved_memories`
- `src/Core/ExecutionContextManager.py` — handler registry fix, `with_retrieved_memories`
- `src/Core/Orchestrator.py` — optional `MemoryManager`
- `src/Core/PromptBuilder.py` — memory section in planner prompt
- `src/Core/history.py` — default empty lists
- `src/Core/RuntimeContext.py` — default `execution_id`
- `src/Types/Plan.py` — `next_pending_step` uses `steps`
- `src/Types/Artifact.py` / `Events.py` — datetime field fixes
- `src/Types/ExecuterResult.py` — alias + response field fix
- `requirements.txt` — pytest, pytest-asyncio

## Architecture (after Module 2)

```
Orchestrator
  ├─ MemoryManager (optional) → retrieve before plan
  ├─ NodeRunner → Nodes → NodeResult
  ├─ ExecutionContextManager → new ExecutionContext (immutable)
  └─ History (append-only)

MemoryManager
  ├─ MemoryStore (records)
  ├─ EmbeddingProvider
  ├─ VectorStore (embeddings)
  └─ MemoryRetriever
```

## Tests

- `tests/test_vector_memory.py` — domain, embeddings, vector search, manager, context, prompts
- `tests/test_orchestrator_memory.py` — orchestrator retrieves before first node

Run: `pytest` from repo root (requires `pip install -r requirements.txt`).

**Last run:** 17 passed, 1 skipped (optional benchmark).

## Known limitations

- WIP codebase: several node/history types still inconsistent (executor/reflector paths not fully green in integration tests beyond memory).
- No persistent memory backend; brute-force in-memory index only.
- No ANN library or vector DB integrated.
- Hash embeddings are for development only.
- No embedding migration/re-embedding pipeline.
- No automatic memory write at end of execution.
- No advanced ranking beyond vector similarity score.

## Next planned component

1. **Durable VectorStore** — pgvector/Qdrant implementing `VectorStore` + optional ANN `search_strategy`.  
2. **Re-embedding job** — batch upgrade when `embedding_version` changes.  
3. **Production EmbeddingProvider** — env-configured API adapter.  
4. **Remember hook** — optional post-run `remember()` from approved reflections (without merging History into Memory).

## History log

- **2026-09-25** — Module 2 vector memory foundation integrated; documentation and tests added.
- **2026-10-08** — Vector memory v1.1: retrieval filters, embedding versioning, brute-force/ANN-ready `VectorStore`, supersede support.
