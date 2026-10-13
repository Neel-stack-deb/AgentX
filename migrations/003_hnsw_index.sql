-- Optional ANN index (HNSW). Apply when PGVECTOR_INDEX_MODE=hnsw.
-- Requires migration 002 (fixed embedding dimensions).

CREATE INDEX IF NOT EXISTS idx_agentx_memories_embedding_hnsw
    ON agentx_memories
    USING hnsw (embedding vector_cosine_ops);
