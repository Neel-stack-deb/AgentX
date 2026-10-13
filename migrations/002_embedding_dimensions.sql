-- pgvector ANN indexes require embedding column to have fixed dimensions.
-- Safe for new DBs (001 may already declare vector(N)) and upgrades from vector without dims.

ALTER TABLE agentx_memories
    ALTER COLUMN embedding TYPE vector({{EMBEDDING_DIMENSION}});
