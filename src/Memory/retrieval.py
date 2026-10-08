"""Retrieval contracts shared by VectorStore and MemoryRetriever."""

from pydantic import BaseModel, Field

from Types.Memory import MemoryStatus, MemoryType


class VectorIndexMetadata(BaseModel):
    """
    Denormalized fields stored alongside each vector for index-time filtering.

    Kept in sync with Memory on write; backends may index these without
    joining MemoryStore on every query.
    """

    memory_type: MemoryType = MemoryType.SEMANTIC
    status: MemoryStatus = MemoryStatus.ACTIVE
    project_id: str | None = None
    scope: str | None = None
    embedding_model: str
    embedding_version: str
    embedding_dimension: int
    superseded_by_memory_id: str | None = None


class VectorIndexRecord(BaseModel):
    memory_id: str
    embedding: list[float]
    metadata: VectorIndexMetadata


class MemoryRetrievalFilter(BaseModel):
    """
    Optional constraints applied before / during vector search.

    Orchestrator and nodes do not construct these; callers of MemoryManager do.
    """

    memory_type: MemoryType | None = None
    status: MemoryStatus | None = MemoryStatus.ACTIVE
    project_id: str | None = None
    scope: str | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    exclude_superseded: bool = Field(
        default=True,
        description="Skip memories that have been superseded by a newer record.",
    )


def metadata_matches_filter(
    metadata: VectorIndexMetadata,
    filters: MemoryRetrievalFilter | None,
) -> bool:
    if filters is None:
        return True

    if filters.memory_type is not None and metadata.memory_type != filters.memory_type:
        return False
    if filters.status is not None and metadata.status != filters.status:
        return False
    if filters.project_id is not None and metadata.project_id != filters.project_id:
        return False
    if filters.scope is not None and metadata.scope != filters.scope:
        return False
    if (
        filters.embedding_model is not None
        and metadata.embedding_model != filters.embedding_model
    ):
        return False
    if (
        filters.embedding_version is not None
        and metadata.embedding_version != filters.embedding_version
    ):
        return False
    if filters.exclude_superseded and metadata.superseded_by_memory_id is not None:
        return False
    return True
