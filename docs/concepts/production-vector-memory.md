# Production Vector Memory — PostgreSQL + pgvector

## IMPLEMENTED NOW vs FUTURE

| Area | Implemented now | Future production work |
|------|-----------------|------------------------|
| Persistence | PostgreSQL single table | Sharding, read replicas |
| Vector search | pgvector SQL (`<=>`, ORDER BY, LIMIT) | Tuned ANN ops per workload |
| ANN | HNSW index via migration `002_hnsw_index.sql` | IVF, index maintenance jobs |
| Consistency | Single-DB transactions (`TransactionalPostgresMemoryManager`) | Cross-region, outbox patterns |
| Embeddings | `HashEmbeddingProvider` + validation | Managed API providers |
| Re-embed | `ReembeddingMigrator` + `scripts/reembed_memories.py` | Background worker, metrics |
| Config | `MEMORY_STORE` / `VECTOR_STORE` env + `build_memory_manager()` | Service mesh, secrets manager |

Connecting pgvector does **not** make AgentX fully production-ready.

---

## 1. Why in-memory is insufficient

In-memory `MemoryStore` / `BruteForceVectorStore` lose data on restart, scan every vector in Python, and cannot share state across processes. Production needs durable metadata, server-side similarity search, and operational tooling (backups, indexes, SQL filters).

## 2. Why pgvector for this phase

- Transactional writes with relational metadata  
- Native vector type and distance operators  
- Optional HNSW ANN indexes  
- Familiar SQL operations model  
- Keeps `VectorStore` swappable (not framework-coupled)

## 3. Architecture (unchanged boundaries)

```
Orchestrator
    → MemoryManager (optional factory wiring)
        → MemoryStore interface → PostgresMemoryStore
        → VectorStore interface → PgVectorStore
        → EmbeddingProvider
        → MemoryRetriever
    → ExecutionContext.with_retrieved_memories()
    → PromptBuilder
```

`build_memory_manager()` selects backends from environment. **Orchestrator does not import postgres modules.**

When both backends are postgres/pgvector, use `TransactionalPostgresMemoryManager` so metadata + embedding commit together.

## 4. Database schema

Table `agentx_memories` (see `migrations/001_initial_schema.sql`):

| Column | Purpose |
|--------|---------|
| `memory_id` | Primary key |
| `content` | Searchable text |
| `memory_type`, `status`, `project_id`, `scope` | Domain + filters |
| `valid_from`, `valid_until` | Temporal validity (stored; policy TBD) |
| `superseded_by_memory_id` | Stale lineage |
| `embedding_*` | Model/version/dimension tags |
| `embedding vector` | pgvector column |

**Indexes (why):**

- `(project_id, scope, status) WHERE active` — tenant-scoped retrieval  
- `(status, memory_type, embedding_model, embedding_version)` — common filter prefix  
- `(valid_from, valid_until)` — future TTL queries  
- `(superseded_by_memory_id)` — lineage maintenance  
- HNSW on `embedding` (`002_hnsw_index.sql`) — ANN search

## 5. VectorStore abstraction

`VectorStore` exposes `upsert`, `delete`, `similarity_search(..., filters)`, and `search_strategy`. `PgVectorStore` delegates to `PostgresMemoryRepository` — no Python full-table cosine scan.

## 6. PostgreSQL + pgvector implementation

- **Writes:** `VectorIndexRecord` validated for dimension; stored with `pgvector.Vector`.  
- **Reads:** SQL `ORDER BY embedding <=> query_vector LIMIT K`.  
- **Similarity semantics:** pgvector returns **cosine distance** via `<=>` with `vector_cosine_ops`. Framework returns **cosine similarity** as `1 - distance` (consistent with normalized dev embeddings).

## 7. Exact vs ANN search

- `PGVECTOR_INDEX_MODE=exact` — disables index scan for the query (`enable_indexscan = off`) for exact ordering over filtered rows.  
- `PGVECTOR_INDEX_MODE=hnsw` — uses HNSW index when present; sets `hnsw.ef_search` (default 40). **Approximate** neighbors; faster at scale.

AgentX does not implement HNSW — PostgreSQL/pgvector does.

## 8. HNSW (concept)

HNSW builds a multi-layer graph to greedy-navigate toward nearest neighbors without scanning all vectors. **Recall vs latency:** lower `ef_search` → faster, may miss true top-K. Higher `ef_search` → better recall, slower.

## 9. Metadata filtering + query planning

Filters are pushed into SQL `WHERE` (status, project_id, scope, memory_type, embedding version, superseded). **Production caveat:** combining restrictive `WHERE` clauses with ANN indexes can change planner behavior vs unconstrained ANN. Postgres may filter before or after index steps depending on statistics — recall and latency can differ from global ANN search. Initial implementation prioritizes correctness and simple SQL.

## 10. Embedding versioning

Each memory stores `embedding_model`, `embedding_version`, `embedding_dimension`. Retrieval can filter by version during mixed rollouts.

**Migration path (manual/batch today):**

```
Embedding V1 vectors → operator runs ReembeddingMigrator → V2 vectors + metadata update
```

Not run at application startup.

## 11. Transaction boundaries

`TransactionalPostgresMemoryManager.remember/update/supersede/delete` uses `PostgresMemoryRepository` transactions so metadata and embedding do not diverge.

**Split wiring** (inmemory + pgvector) is discouraged; factory uses transactional manager only when both are postgres.

## 12. Connection pooling

`psycopg_pool.ConnectionPool` with `PG_POOL_MIN_SIZE`, `PG_POOL_MAX_SIZE`, `PG_POOL_TIMEOUT_SECONDS`. Connections register pgvector types on checkout via `configure=`. No per-query TCP connect.

AgentX nodes are async; memory I/O remains **sync** today — call from orchestrator without blocking the event loop only if memory calls stay short (documented limitation).

## 13. Failure modes

| Failure | Handling |
|---------|----------|
| DB unavailable | `DatabaseUnavailableError` |
| Dimension mismatch | `EmbeddingDimensionError` before write |
| Duplicate `memory_id` | `MemoryDuplicateError` (SQL 23505) |
| Missing memory on vector upsert | `MemoryNotFoundError` |
| Partial write (postgres transactional path) | Rollback |
| Split inmemory/postgres stores | Not transactional — avoid |
| Schema migration failure | `apply_migrations.py` exits non-zero |
| Timeout / pool exhaustion | psycopg pool timeout surfaces to caller |
| No results | Empty list (not an error) |
| Superseded | Filtered via SQL + retriever |

Not implemented: automatic retries, circuit breakers, dead-letter queues.

## 14. MemoryStore vs VectorStore consistency

Single table, shared repository. Interface split preserved for future Pinecone vector-only backends; postgres implementation keeps one source of truth.

## 15. Testing strategy

- **Fast unit tests:** in-memory stores, mocks, validation (default `pytest`).  
- **Integration:** `tests/integration/` with `AGENTX_PG_INTEGRATION=1` + Docker Compose Postgres.  
- **Benchmarks:** `AGENTX_RUN_BENCH=1` + integration flag; not part of default CI.

## 16. Benchmark methodology

`tests/benchmarks/test_pgvector_comparison_bench.py` compares median latency for brute-force in-memory vs pgvector exact vs HNSW at configurable `AGENTX_BENCH_N`. Recall@K measurement left for future bench expansion.

## 17. Observability

`observe_retrieval` logs backend, strategy, top_k, result count, latency, filter keys — **not** content or embeddings.

## 18. Pinecone readiness (design note)

**Shared VectorStore contract:** `upsert(VectorIndexRecord)`, `similarity_search(embedding, top_k, filters)`, `delete`, `search_strategy`.

| Concern | pgvector | Pinecone (future) |
|---------|----------|-------------------|
| IDs | `memory_id` UUID | External vector id |
| Metadata filters | SQL WHERE | Pinecone metadata filter JSON |
| Distance | `<=>` cosine distance | Index metric config |
| ANN | HNSW index | Managed ANN |
| Transactions with MemoryStore | Same Postgres row | Requires dual-write or metadata-only in Postgres |

`PineconeVectorStore` could be added without changing Orchestrator, Nodes, ExecutionContext, PromptBuilder, or `MemoryManager` public API.

## 19. What is NOT production-ready yet

- No managed embedding API wired by default  
- No automatic re-embed worker  
- No reranking, compression, or post-run remember  
- Sync DB from async orchestrator  
- No multi-tenant hardening beyond `scope`/`project_id` fields  
- No Pinecone / distributed memory service

## Configuration

See `.env.example`: `MEMORY_STORE`, `VECTOR_STORE`, `DATABASE_URL`, `PGVECTOR_INDEX_MODE`, pool settings.

Local DB: `docker compose up -d` then `DATABASE_URL=... python scripts/apply_migrations.py`.
