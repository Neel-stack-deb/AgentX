# Memory Retrieval and Ranking

## Pipeline

```
Query
  → EmbeddingProvider (query vector)
  → VectorStore similarity search (candidate pool)
  → Hard eligibility filters (Memory record validation)
  → MemoryRanker (weighted scoring)
  → Top-K ScoredMemory
  → ExecutionContext.retrieved_memories
  → PromptBuilder
  → LLM
```

Eligibility is **not** ranking. Unauthorized, superseded, deleted, or out-of-validity memories are excluded before scores are combined.

## Hard eligibility (`Memory/eligibility.py`)

Enforced on hydrated `Memory` records after vector search (and in addition to backend SQL filters where supported).

| Rule | Semantics (UTC) |
|------|------------------|
| `status` / `project_id` / `scope` / embedding tags | Must match `MemoryRetrievalFilter` when set |
| `DELETED` | Never eligible |
| `superseded_by_memory_id` | Excluded when `exclude_superseded=True` |
| `valid_from` | Eligible when `now >= valid_from` (inclusive) |
| `valid_until` | Eligible when `now <= valid_until` (inclusive) |

**Backend gap:** PostgreSQL/pgvector SQL filters do not yet apply `valid_from` / `valid_until`. Eligibility is enforced post-hydration in `VectorMemoryRetriever`. ANN + SQL filters may return candidates that fail validity checks after hydration.

## Candidate pool vs final top-K

`RankingConfig.candidate_pool_size(top_k) = max(top_k, top_k * candidate_multiplier, min_candidate_pool)`.

Default: multiplier **4**, minimum pool **20**.

| Larger pool | Effect |
|-------------|--------|
| Pros | Better recall for ranking signals that differ from raw similarity |
| Cons | More vector work and hydration |

## Ranking (`Memory/ranking.py`)

**Strategy id:** `weighted_v1` (`WeightedMemoryRanker`)

Signals (each normalized to **[0, 1]**):

| Signal | Source |
|--------|--------|
| Similarity | Vector candidate score (cosine similarity) |
| Recency | `exp(-age_hours / half_life)` from `updated_at` |
| Importance | `memory.importance` or default 0.5 |
| Confidence | `memory.confidence` or default 0.5 |
| Lexical overlap | Token overlap(query, content) / |query tokens| (optional weight) |

**Composite score:**

```
composite = (w_sim*s_sim + w_rec*s_rec + w_imp*s_imp + w_conf*s_conf + w_lex*s_lex) / sum(w_i)
```

**Default weights:** similarity **0.55**, recency **0.20**, importance **0.15**, confidence **0.10**, lexical **0.0**.

**Tie-break:** descending `composite`, then `similarity`, then `memory_id`.

`ScoredMemory.score` is the **final ranking composite**. `similarity_score` and `ranking_breakdown` preserve diagnostics.

Replace ranking by implementing `MemoryRanker` and injecting it into `VectorMemoryRetriever`.

## Configuration

Pass `RankingConfig` to `MemoryManager(..., ranking_config=...)`.

No LLM reranking, BM25, or hybrid search in this module.

## Observability

`MemoryManager.retrieve_with_diagnostics()` returns `RetrievalOutcome` with counts and retrieval/ranking latency. Logs exclude raw content and embeddings.

## Trade-offs

Weighted linear fusion is explainable and fast but not universally optimal. Similarity-heavy defaults preserve behavior close to pre-ranking vector order when metadata is uniform.
