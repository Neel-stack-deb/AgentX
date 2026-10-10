-- AgentX vector memory: initial schema (run via scripts/apply_migrations.py)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agentx_memories (
    memory_id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    project_id TEXT,
    scope TEXT,
    status TEXT NOT NULL,
    source TEXT,
    importance DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    superseded_by_memory_id UUID,
    embedding_model TEXT,
    embedding_version TEXT,
    embedding_dimension INTEGER,
    embedding vector
);

-- Primary key already indexes memory_id.

-- Composite filter for tenant-scoped active retrieval (project + scope + status).
CREATE INDEX IF NOT EXISTS idx_agentx_memories_project_scope_active
    ON agentx_memories (project_id, scope, status)
    WHERE status = 'active';

-- Filter dimensions commonly combined with vector search.
CREATE INDEX IF NOT EXISTS idx_agentx_memories_retrieval_filters
    ON agentx_memories (status, memory_type, embedding_model, embedding_version);

-- Temporal validity lookups (future TTL / validity policies).
CREATE INDEX IF NOT EXISTS idx_agentx_memories_validity
    ON agentx_memories (valid_from, valid_until);

-- Supersede lineage checks.
CREATE INDEX IF NOT EXISTS idx_agentx_memories_superseded
    ON agentx_memories (superseded_by_memory_id)
    WHERE superseded_by_memory_id IS NOT NULL;
