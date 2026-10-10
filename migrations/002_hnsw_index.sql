-- Optional ANN index (HNSW). Apply when PGVECTOR_INDEX_MODE=hnsw.
-- Uses cosine distance operator class; queries use <=> and convert distance to similarity.

CREATE INDEX IF NOT EXISTS idx_agentx_memories_embedding_hnsw
    ON agentx_memories
    USING hnsw (embedding vector_cosine_ops);
