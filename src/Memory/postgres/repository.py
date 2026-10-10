from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import UUID

from pgvector import Vector
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from Memory.backend_config import MemoryBackendSettings, PgVectorIndexMode
from Memory.embedding_validation import validate_embedding_vector
from Memory.exceptions import (
    DatabaseUnavailableError,
    EmbeddingDimensionError,
    MemoryDuplicateError,
    MemoryNotFoundError,
)
from Memory.postgres.pool import validate_table_name
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexRecord
from Memory.vector_store import VectorSearchStrategy
from Types.Memory import Memory, MemoryStatus, MemoryType


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def _row_to_memory(row: dict[str, Any]) -> Memory:
    return Memory(
        memory_id=str(row["memory_id"]),
        content=row["content"],
        memory_type=MemoryType(row["memory_type"]),
        project_id=row["project_id"],
        scope=row["scope"],
        status=MemoryStatus(row["status"]),
        source=row["source"],
        importance=row["importance"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
        superseded_by_memory_id=(
            str(row["superseded_by_memory_id"])
            if row["superseded_by_memory_id"]
            else None
        ),
        embedding_model=row["embedding_model"],
        embedding_version=row["embedding_version"],
        embedding_dimension=row["embedding_dimension"],
    )


class PostgresMemoryRepository:
    """
    Single-table persistence for Memory metadata + pgvector embedding.

    MemoryStore and PgVectorStore delegate here to keep rows consistent.
    """

    def __init__(self, pool: ConnectionPool, settings: MemoryBackendSettings) -> None:
        self._pool = pool
        self._settings = settings
        self._table = validate_table_name(settings.pg_table)

    @property
    def table(self) -> str:
        return self._table

    @property
    def search_strategy(self) -> VectorSearchStrategy:
        if self._settings.pgvector_index_mode == PgVectorIndexMode.HNSW:
            return VectorSearchStrategy.ANN
        return VectorSearchStrategy.BRUTE_FORCE

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        try:
            with self._pool.connection() as conn:
                yield conn
        except Exception as exc:
            raise DatabaseUnavailableError(str(exc)) from exc

    def save_memory(self, memory: Memory) -> Memory:
        with self.connection() as conn:
            try:
                with conn.transaction():
                    self._insert_memory(conn, memory)
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "23505":
                    raise MemoryDuplicateError(str(memory.memory_id)) from exc
                raise
        return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        sql = f"SELECT * FROM {self._table} WHERE memory_id = %s"
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (_parse_uuid(memory_id),))
                row = cur.fetchone()
        return _row_to_memory(row) if row else None

    def update_memory(self, memory: Memory) -> Memory:
        memory = memory.model_copy(
            update={"updated_at": datetime.now(timezone.utc)},
        )
        sql = f"""
            UPDATE {self._table}
            SET content = %s,
                memory_type = %s,
                project_id = %s,
                scope = %s,
                status = %s,
                source = %s,
                importance = %s,
                updated_at = %s,
                valid_from = %s,
                valid_until = %s,
                superseded_by_memory_id = %s,
                embedding_model = %s,
                embedding_version = %s,
                embedding_dimension = %s
            WHERE memory_id = %s
        """
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            memory.content,
                            memory.memory_type.value,
                            memory.project_id,
                            memory.scope,
                            memory.status.value,
                            memory.source,
                            memory.importance,
                            memory.updated_at,
                            memory.valid_from,
                            memory.valid_until,
                            (
                                _parse_uuid(memory.superseded_by_memory_id)
                                if memory.superseded_by_memory_id
                                else None
                            ),
                            memory.embedding_model,
                            memory.embedding_version,
                            memory.embedding_dimension,
                            _parse_uuid(memory.memory_id),
                        ),
                    )
                    if cur.rowcount == 0:
                        raise MemoryNotFoundError(memory.memory_id)
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        """Soft-delete metadata and remove embedding in one transaction."""
        sql = f"""
            UPDATE {self._table}
            SET status = %s, embedding = NULL, updated_at = %s
            WHERE memory_id = %s AND status != %s
        """
        now = datetime.now(timezone.utc)
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            MemoryStatus.DELETED.value,
                            now,
                            _parse_uuid(memory_id),
                            MemoryStatus.DELETED.value,
                        ),
                    )
                    return cur.rowcount > 0

    def soft_delete_memory(self, memory_id: str) -> bool:
        sql = f"""
            UPDATE {self._table}
            SET status = %s, updated_at = %s
            WHERE memory_id = %s AND status != %s
        """
        now = datetime.now(timezone.utc)
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            MemoryStatus.DELETED.value,
                            now,
                            _parse_uuid(memory_id),
                            MemoryStatus.DELETED.value,
                        ),
                    )
                    return cur.rowcount > 0

    def list_active_memories(self) -> list[Memory]:
        sql = f"""
            SELECT * FROM {self._table}
            WHERE status = %s
            ORDER BY created_at DESC
        """
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (MemoryStatus.ACTIVE.value,))
                rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def upsert_vector(self, record: VectorIndexRecord) -> None:
        validate_embedding_vector(
            record.embedding,
            expected_dimension=record.metadata.embedding_dimension,
        )
        sql = f"""
            UPDATE {self._table}
            SET embedding = %s,
                embedding_model = %s,
                embedding_version = %s,
                embedding_dimension = %s,
                memory_type = %s,
                status = %s,
                project_id = %s,
                scope = %s,
                superseded_by_memory_id = %s,
                updated_at = %s
            WHERE memory_id = %s
        """
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            Vector(record.embedding),
                            record.metadata.embedding_model,
                            record.metadata.embedding_version,
                            record.metadata.embedding_dimension,
                            record.metadata.memory_type.value,
                            record.metadata.status.value,
                            record.metadata.project_id,
                            record.metadata.scope,
                            (
                                _parse_uuid(record.metadata.superseded_by_memory_id)
                                if record.metadata.superseded_by_memory_id
                                else None
                            ),
                            datetime.now(timezone.utc),
                            _parse_uuid(record.memory_id),
                        ),
                    )
                    if cur.rowcount == 0:
                        raise MemoryNotFoundError(record.memory_id)

    def delete_vector(self, memory_id: str) -> bool:
        sql = f"""
            UPDATE {self._table}
            SET embedding = NULL, updated_at = %s
            WHERE memory_id = %s
        """
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        sql, (datetime.now(timezone.utc), _parse_uuid(memory_id))
                    )
                    return cur.rowcount > 0

    def save_memory_with_vector(
        self, memory: Memory, record: VectorIndexRecord
    ) -> None:
        validate_embedding_vector(
            record.embedding,
            expected_dimension=record.metadata.embedding_dimension,
        )
        with self.connection() as conn:
            with conn.transaction():
                try:
                    self._insert_memory(conn, memory)
                except Exception as exc:
                    if getattr(exc, "sqlstate", None) == "23505":
                        raise MemoryDuplicateError(str(memory.memory_id)) from exc
                    raise
                self._update_vector_in_tx(conn, record)

    def update_memory_with_vector(
        self, memory: Memory, record: VectorIndexRecord
    ) -> Memory:
        validate_embedding_vector(
            record.embedding,
            expected_dimension=record.metadata.embedding_dimension,
        )
        updated = memory.model_copy(
            update={"updated_at": datetime.now(timezone.utc)},
        )
        with self.connection() as conn:
            with conn.transaction():
                self._update_memory_in_tx(conn, updated)
                self._update_vector_in_tx(conn, record)
        return updated

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: MemoryRetrievalFilter | None,
    ) -> list[tuple[str, float]]:
        if top_k <= 0:
            return []

        where_sql, params = self._build_filter_clause(filters)
        query_vec = Vector(query_embedding)

        # pgvector cosine distance <=>; similarity = 1 - distance (for normalized vectors).
        sql = f"""
            SELECT memory_id,
                   1 - (embedding <=> %s) AS similarity
            FROM {self._table}
            WHERE embedding IS NOT NULL
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        params = [query_vec, *params, query_vec, top_k]

        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor(row_factory=dict_row) as cur:
                    if self._settings.pgvector_index_mode == PgVectorIndexMode.HNSW:
                        cur.execute(
                            "SET LOCAL hnsw.ef_search = %s",
                            (self._settings.hnsw_ef_search,),
                        )
                    if self._settings.pgvector_index_mode == PgVectorIndexMode.EXACT:
                        cur.execute("SET LOCAL enable_indexscan = off")

                    cur.execute(sql, params)
                    rows = cur.fetchall()

        return [(str(row["memory_id"]), float(row["similarity"])) for row in rows]

    def list_memories_for_reembedding(
        self,
        *,
        embedding_model: str | None,
        embedding_version: str,
        limit: int = 100,
    ) -> list[Memory]:
        clauses = ["embedding_version = %s"]
        params: list[Any] = [embedding_version]
        if embedding_model is not None:
            clauses.append("embedding_model = %s")
            params.append(embedding_model)
        sql = f"""
            SELECT * FROM {self._table}
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at ASC
            LIMIT %s
        """
        params.append(limit)
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def _insert_memory(self, conn: Connection, memory: Memory) -> None:
        sql = f"""
            INSERT INTO {self._table} (
                memory_id, content, memory_type, project_id, scope, status,
                source, importance, created_at, updated_at, valid_from, valid_until,
                superseded_by_memory_id, embedding_model, embedding_version,
                embedding_dimension, embedding
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    _parse_uuid(memory.memory_id),
                    memory.content,
                    memory.memory_type.value,
                    memory.project_id,
                    memory.scope,
                    memory.status.value,
                    memory.source,
                    memory.importance,
                    memory.created_at,
                    memory.updated_at,
                    memory.valid_from,
                    memory.valid_until,
                    (
                        _parse_uuid(memory.superseded_by_memory_id)
                        if memory.superseded_by_memory_id
                        else None
                    ),
                    memory.embedding_model,
                    memory.embedding_version,
                    memory.embedding_dimension,
                    None,
                ),
            )

    def _update_memory_in_tx(self, conn: Connection, memory: Memory) -> None:
        sql = f"""
            UPDATE {self._table}
            SET content = %s,
                memory_type = %s,
                project_id = %s,
                scope = %s,
                status = %s,
                source = %s,
                importance = %s,
                updated_at = %s,
                valid_from = %s,
                valid_until = %s,
                superseded_by_memory_id = %s,
                embedding_model = %s,
                embedding_version = %s,
                embedding_dimension = %s
            WHERE memory_id = %s
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    memory.content,
                    memory.memory_type.value,
                    memory.project_id,
                    memory.scope,
                    memory.status.value,
                    memory.source,
                    memory.importance,
                    memory.updated_at,
                    memory.valid_from,
                    memory.valid_until,
                    (
                        _parse_uuid(memory.superseded_by_memory_id)
                        if memory.superseded_by_memory_id
                        else None
                    ),
                    memory.embedding_model,
                    memory.embedding_version,
                    memory.embedding_dimension,
                    _parse_uuid(memory.memory_id),
                ),
            )
            if cur.rowcount == 0:
                raise MemoryNotFoundError(memory.memory_id)

    def _update_vector_in_tx(self, conn: Connection, record: VectorIndexRecord) -> None:
        sql = f"""
            UPDATE {self._table}
            SET embedding = %s,
                embedding_model = %s,
                embedding_version = %s,
                embedding_dimension = %s,
                memory_type = %s,
                status = %s,
                project_id = %s,
                scope = %s,
                superseded_by_memory_id = %s,
                updated_at = %s
            WHERE memory_id = %s
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    Vector(record.embedding),
                    record.metadata.embedding_model,
                    record.metadata.embedding_version,
                    record.metadata.embedding_dimension,
                    record.metadata.memory_type.value,
                    record.metadata.status.value,
                    record.metadata.project_id,
                    record.metadata.scope,
                    (
                        _parse_uuid(record.metadata.superseded_by_memory_id)
                        if record.metadata.superseded_by_memory_id
                        else None
                    ),
                    datetime.now(timezone.utc),
                    _parse_uuid(record.memory_id),
                ),
            )
            if cur.rowcount == 0:
                raise MemoryNotFoundError(record.memory_id)

    def _build_filter_clause(
        self, filters: MemoryRetrievalFilter | None
    ) -> tuple[str, list[Any]]:
        if filters is None:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []

        if filters.status is not None:
            clauses.append("AND status = %s")
            params.append(filters.status.value)
        if filters.memory_type is not None:
            clauses.append("AND memory_type = %s")
            params.append(filters.memory_type.value)
        if filters.project_id is not None:
            clauses.append("AND project_id = %s")
            params.append(filters.project_id)
        if filters.scope is not None:
            clauses.append("AND scope = %s")
            params.append(filters.scope)
        if filters.embedding_model is not None:
            clauses.append("AND embedding_model = %s")
            params.append(filters.embedding_model)
        if filters.embedding_version is not None:
            clauses.append("AND embedding_version = %s")
            params.append(filters.embedding_version)
        if filters.exclude_superseded:
            clauses.append("AND superseded_by_memory_id IS NULL")

        return " ".join(clauses), params
