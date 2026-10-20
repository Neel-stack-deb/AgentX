# Hierarchical Memory in AgentX

Hierarchical memory organizes **summaries at increasing scope** with pointers to detailed `Memory` records. Logical levels:

1. **Global** — persistent agent-wide overview  
2. **Project** — summary for a project id  
3. **Topic** — subject within a project  
4. **Detail** — underlying `Memory` rows referenced by `source_memory_ids`

These are scopes in one store, not separate databases.

## 1. Concept

Vector memory stores many granular facts. Operators and planners often need **compressed views** first, then drill-down. Summaries are versioned documents with explicit provenance (`source_memory_ids`) and parent links (`parent_summary_id`).

## 2. Architecture

| Piece | Role |
|-------|------|
| `MemorySummary` | Scope, content, version, status, provenance |
| `InMemoryHierarchicalSummaryStore` | CRUD, current-summary selection, stale + regenerate |
| `HierarchicalMemoryRetriever` | Deterministic intent-based retrieval |

```
MemorySummary (GLOBAL)
    └── parent_summary_id → PROJECT summary
            └── TOPIC summary
                    └── source_memory_ids → MemoryStore.get(...)
```

## 3. Data flow

**Write (manual in v1):** `create(MemorySummary(...))` with supplied `content`.

**Read:** `HierarchicalMemoryRetriever.retrieve(intent, scope_type, scope_id)`:

| Intent | Behavior |
|--------|----------|
| `overview` | `get_current_summary(scope_type, scope_id)` |
| `topic` | current TOPIC summary for `topic_scope_id` or `scope_id` |
| `detail` | load memories for `source_memory_ids` on the anchor summary |

`insufficient_evidence=True` when no current summary or memories are missing.

**Provenance:** `mark_stale_for_memory(memory_id)` sets dependent ACTIVE summaries to `STALE`. `regenerate(summary_id, new_content)` supersedes the old row and creates `version + 1`.

`get_current_summary` returns only **ACTIVE** rows with the highest `version`.

## 4. Design decisions

- No automatic summarization LLM — content is provided explicitly.
- Stale and superseded rows remain in the store for audit; they are not “current.”
- Retrieval intents are explicit enums (no LLM planning).

## 5. Example

```python
from Memory.hierarchical import InMemoryHierarchicalSummaryStore, HierarchicalMemoryRetriever
from Types.HierarchicalMemory import MemorySummary, SummaryScopeType, HierarchicalRetrievalIntent

store = InMemoryHierarchicalSummaryStore()
store.create(
    MemorySummary(
        scope_type=SummaryScopeType.GLOBAL,
        scope_id="agentx",
        content="AgentX coordinates nodes via Orchestrator.",
        source_memory_ids=[memory_id],
    )
)
retriever = HierarchicalMemoryRetriever(summary_store=store, memory_store=memory_store)
retriever.retrieve(HierarchicalRetrievalIntent.OVERVIEW, scope_type=SummaryScopeType.GLOBAL, scope_id="agentx")
```

## 6. Tests

```bash
pytest tests/test_hierarchical_memory.py -q
```

## 7. Limitations

- In-memory only; no Postgres table yet.
- `MemoryManager.update` does not auto-mark summaries stale until integration milestone (explicit `mark_stale_for_memory` today).
- No background regeneration jobs.

Future: hook summary invalidation into `MemoryManager.update`, optional summary generation, orchestrator context injection for overview intents.
