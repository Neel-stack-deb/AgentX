# AgentX Project Status

**Source of truth.** Status reflects what exists in the repository and what has been **verified by automated tests**, not aspirational production readiness.

## Version

**0.4.0-dev** — Module 2: vector memory + pgvector backend + retrieval/ranking layer (v0.4).

## Verification legend

| Label | Meaning |
|-------|---------|
| **Verified (unit)** | Covered by default `pytest` (no live database). |
| **Verified (integration)** | Requires `AGENTX_PG_INTEGRATION=1` and a running Postgres with pgvector + applied migrations. |
| **Implemented, not verified** | Code/docs/migrations present; not exercised in CI or last local run against live DB. |
| **Partial** | Foundation or optional path only; gaps documented. |
| **Not implemented** | Missing or explicitly out of scope. |

## Module 1 — Core agent loop

| Component | Status | Verification | Notes |
|-----------|--------|--------------|-------|
| Orchestrator | Implemented | Unit (memory retrieve mock) | Does not call `build_memory_manager()`; inject `MemoryManager` manually. |
| RuntimeContext | Implemented | Indirect | Default `execution_id`. |
| ExecutionContext | Implemented | Unit | Immutable; `retrieved_memories`. |
| ExecutionContextManager | Implemented | Unit | `with_retrieved_memories`; node handlers still WIP in places. |
| History | Implemented | Limited | Append-only; executor/reflector paths inconsistent. |
| Nodes (Planner, Executer, Reflector) | Implemented | Partial | No full E2E agent test suite. |
| NodeRunner | Implemented | Indirect | |
| PromptBuilder | Implemented | Unit | Planner includes retrieved memories. |
| LLM (BaseLLMClient, MockLLMClient) | Partial | Manual | Mock only in tree. |
| Artifacts & Events | Implemented | Limited | |
| Scratchpad | Implemented | — | |
| ADRs 001–005 | Documented | — | Under `src/Docs/ADR/` |

## Module 2 — Agent Memory

| Component | Status | Verification | Notes |
|-----------|--------|--------------|-------|
| Memory domain (`Types/Memory.py`) | Done (v1.1) | Unit | Includes embedding tags, `project_id`/`scope`, supersede, `valid_from`/`valid_until`. |
| `HashEmbeddingProvider` | Done (v1.1) | Unit | Only default embedding implementation. |
| Production `EmbeddingProvider` | Not implemented | — | No HTTP/API provider in tree. |
| `BruteForceVectorStore` / in-memory | Done (v1.1) | Unit | Default when env not set. |
| `MemoryStore` / `InMemoryMemoryStore` | Done (v1) | Unit | |
| `MemoryRetriever` / filters | Done (v1.1) | Unit | |
| `MemoryManager` (in-memory path) | Done (v1.1) | Unit | remember/retrieve/update/delete/supersede. |
| `PostgresMemoryStore` | Implemented (v0.3) | Integration only | `src/Memory/postgres/postgres_memory_store.py`. |
| `PgVectorStore` | Implemented (v0.3) | Unit (mock repo) + integration opt-in | SQL search in `repository.py`; unit tests mock repository. |
| `PostgresMemoryRepository` | Implemented (v0.3) | Integration opt-in | Single table `agentx_memories`. |
| `TransactionalPostgresMemoryManager` | Implemented (v0.3) | Integration opt-in | Used when `MEMORY_STORE=postgres` and `VECTOR_STORE=pgvector`. |
| `build_memory_manager()` / env config | Implemented (v0.3) | Unit (in-memory default) | `MEMORY_STORE`, `VECTOR_STORE`, `DATABASE_URL`, pool + pgvector settings. |
| Connection pooling | Implemented (v0.3) | Integration opt-in | `psycopg_pool` in `postgres/pool.py`. |
| SQL migrations | Implemented (v0.3) | Manual | `migrations/001_*.sql`, `002_hnsw_index.sql`; `scripts/apply_migrations.py`. |
| Docker Compose (local Postgres) | Implemented (v0.3) | Manual | `docker-compose.yml`; not required for default tests. |
| HNSW ANN index | Implemented (v0.3) | Integration opt-in | Migration `002`; `PGVECTOR_INDEX_MODE=hnsw`, `hnsw.ef_search` in repository. Not validated on live DB in last CI/local default run. |
| Exact pgvector search mode | Implemented (v0.3) | Integration opt-in | `PGVECTOR_INDEX_MODE=exact` disables index scan for query. |
| IVF / external ANN libs | Not implemented | — | |
| `ReembeddingMigrator` + CLI | Partial (v0.3) | Not tested | `reembedding.py`, `scripts/reembed_memories.py`; no pytest coverage. |
| Observability (retrieval logs) | Partial (v0.3) | Manual | `observability.py`; used by `PgVectorStore`. |
| Orchestrator + memory | Done (v1) | Unit | Optional `MemoryManager`; still in-memory unless caller wires postgres factory. |
| Memory eligibility (hard filters) | Done (v0.4) | Unit | `eligibility.py`; validity window on hydrated records. |
| Memory ranking (`weighted_v1`) | Done (v0.4) | Unit | `ranking.py`, `WeightedMemoryRanker`; not LLM reranking. |
| Retrieval diagnostics | Done (v0.4) | Unit | `retrieve_with_diagnostics()` / `RetrievalOutcome`. |
| `confidence` on `Memory` | Done (v0.4) | Unit | Optional 0..1 signal for ranking. |
| Knowledge graph memory (`InMemoryKnowledgeGraphStore`) | Done (v0.5 milestone 1) | Unit | `src/Memory/knowledge_graph/`, `Types/KnowledgeGraph.py`; not wired to `MemoryManager` yet. |
| Hybrid memory (`HybridMemoryRetriever`) | Done (v0.5 milestone 2) | Unit | Vector retriever + graph BFS; `Types/HybridMemory.py`. |
| Hierarchical summaries | Not started | — | Milestone 3 |
| BM25 / LLM rerank | Not started | — | Out of scope |

## Vector memory — current behavior

**Default runtime (verified by unit tests):**

- `MEMORY_STORE` / `VECTOR_STORE` unset or `inmemory` → `MemoryManager` + `InMemoryMemoryStore` + `BruteForceVectorStore`.
- Orchestrator: optional `memory_manager.retrieve(goal.description)` → `with_retrieved_memories` → planner prompt.
- Retrieval: vector **candidate pool** → hard eligibility → **weighted ranking** → top-K (`docs/concepts/memory-retrieval-ranking.md`).

**When explicitly configured (`build_memory_manager` + `DATABASE_URL`):**

- Postgres metadata + pgvector similarity in SQL (`<=>`, similarity `1 - distance`).
- Metadata filters pushed into SQL `WHERE`.
- Transactional writes when both backends are postgres + pgvector.
- HNSW index created only if migration `002` applied and `PGVECTOR_INDEX_MODE=hnsw`.

See [docs/concepts/vector-memory.md](docs/concepts/vector-memory.md) and [docs/concepts/production-vector-memory.md](docs/concepts/production-vector-memory.md).

## Architecture

```
Orchestrator (injects MemoryManager; does not select backend)
  ├─ MemoryManager ← build_memory_manager() [optional wiring]
  │     ├─ MemoryStore     → InMemoryMemoryStore | PostgresMemoryStore
  │     ├─ VectorStore     → BruteForceVectorStore | PgVectorStore
  │     ├─ EmbeddingProvider (HashEmbeddingProvider today)
  │     └─ MemoryRetriever → eligibility → MemoryRanker
  ├─ NodeRunner → Nodes
  ├─ ExecutionContextManager
  └─ History (append-only; separate from Memory)

Postgres path (shared):
  PostgresMemoryStore / PgVectorStore → PostgresMemoryRepository → pooled PostgreSQL (agentx_memories)
  TransactionalPostgresMemoryManager when both stores are postgres/pgvector
```

## Tests (last run)

Command: `pytest` from repo root without `AGENTX_PG_INTEGRATION` / `AGENTX_RUN_BENCH` (2026-10-20).

| Result | Count |
|--------|------|
| Passed | 45 |
| Skipped | 6 |
| Failed | 0 |

**Unit modules include:** `test_vector_memory.py`, `test_ranking.py`, `test_eligibility.py`, `test_orchestrator_memory.py`, `test_embedding_validation.py`, `test_pgvector_unit.py`, `test_knowledge_graph_memory.py`, `test_hybrid_memory.py`.

**Skipped unless opt-in:**

- `tests/integration/test_pgvector_integration.py` (3)
- `tests/integration/test_pgvector_ranking_integration.py` (1)
- `tests/benchmarks/*` (2)

Run integration: `$env:AGENTX_PG_INTEGRATION="1"; pytest tests/integration -q`

## Key files (Module 2)

**In-memory / shared:**

- `src/Types/Memory.py`, `src/Types/KnowledgeGraph.py`, `src/Memory/*.py` (manager, stores, retrieval, ranking, eligibility, factory, …)
- `src/Memory/knowledge_graph/` — entity/relationship graph store

**PostgreSQL / pgvector (v0.3):**

- `src/Memory/postgres/` — pool, repository, stores, transactional manager
- `migrations/001_initial_schema.sql`, `migrations/002_hnsw_index.sql`
- `scripts/apply_migrations.py`, `scripts/reembed_memories.py`
- `docker-compose.yml`, `.env.example`

**Tests:**

- `tests/test_vector_memory.py`, `tests/test_ranking.py`, `tests/test_eligibility.py`, …
- `tests/integration/test_pgvector_integration.py`, `tests/integration/test_pgvector_ranking_integration.py`
- `tests/benchmarks/test_bruteforce_vector_bench.py`, `tests/benchmarks/test_pgvector_comparison_bench.py`

**Docs:**

- `docs/concepts/vector-memory.md`, `docs/concepts/production-vector-memory.md`, `docs/concepts/memory-retrieval-ranking.md`
- `docs/concepts/knowledge-graph-memory.md`, `docs/concepts/hybrid-memory.md`

## Known limitations (accurate)

- **Default path is still in-memory** unless the application calls `build_memory_manager()` with postgres env vars.
- **Postgres/pgvector is not proven in this repo’s default test run**; integration is opt-in and was skipped.
- **HNSW** is defined in migration + query session settings; recall/latency not benchmarked in default CI.
- **Re-embedding** has no automated tests; no background worker.
- **Split backend** (`postgres` memory + `inmemory` vector) is possible via factory but **not transactional** — discouraged.
- **Sync** memory I/O while Orchestrator/nodes are **async**.
- Hash embeddings only; no production embedding API.
- **Validity filters** not pushed into pgvector SQL (post-hydration only).
- No LLM reranking, BM25, post-run remember, compression, Pinecone, or distributed memory service.
- Module 1 executor/reflector/history inconsistencies remain outside memory unit tests.

## Next planned components

1. **Run and gate integration tests** — CI or documented local step with Docker Compose + `AGENTX_PG_INTEGRATION=1`.
2. **Production `EmbeddingProvider`** — env-configured API adapter with dimension validation.
3. **Re-embedding** — tests for `ReembeddingMigrator`; optional scheduled job (not at startup).
4. **Application wiring** — compose Orchestrator with `build_memory_manager()` in app entrypoint (not in framework yet).
5. **Remember hook** — optional post-run `remember()` without merging History into Memory.
6. **SQL validity filters** — optional `valid_from`/`valid_until` in postgres repository WHERE clause.

## History log

- **2026-09-25** — Module 2 vector memory foundation; in-memory store, orchestrator hook, docs, initial tests.
- **2026-10-08** — Vector memory v1.1: retrieval filters, embedding versioning on domain model, `BruteForceVectorStore` + `VectorSearchStrategy`, supersede.
- **2026-10-08** — Vector memory v0.3 (code): PostgreSQL + pgvector (`PostgresMemoryRepository`, `PostgresMemoryStore`, `PgVectorStore`), migrations, Docker Compose, pooling, transactional manager, re-embed migrator + CLI, production doc. **Integration/benchmark verification pending** unless opt-in env is used.
- **2026-10-10** — `PROJECT_STATUS.md` reconciled with repository audit; contradictions between v0.3 code and “in-memory only” limitations removed.
- **2026-10-10** — v0.4: weighted memory ranking, hard eligibility, `confidence` field, retrieval diagnostics; docs `memory-retrieval-ranking.md`.
- **2026-10-20** — v0.5 milestone 1: in-memory knowledge graph (`KnowledgeGraphStore`, BFS traversal, cycle-safe); `docs/concepts/knowledge-graph-memory.md`.
- **2026-10-20** — v0.5 milestone 2: `HybridMemoryRetriever` (vector + graph, deduped ids); `docs/concepts/hybrid-memory.md`.
