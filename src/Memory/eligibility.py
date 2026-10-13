"""Hard eligibility constraints applied before ranking (not soft scores)."""

from datetime import datetime, timezone

from Memory.retrieval import MemoryRetrievalFilter
from Types.Memory import Memory, MemoryStatus


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def is_memory_eligible(
    memory: Memory,
    filters: MemoryRetrievalFilter,
    *,
    now: datetime | None = None,
) -> bool:
    """
    Eligibility semantics (UTC):

    - status / project / scope / embedding tags: must match filter when filter field is set.
    - superseded: excluded when filters.exclude_superseded is True.
    - valid_from: eligible when now >= valid_from (inclusive).
    - valid_until: eligible when now <= valid_until (inclusive end of validity window).
    - Missing validity bounds impose no constraint on that side.
    """
    if filters.status is not None and memory.status != filters.status:
        return False
    if memory.status == MemoryStatus.DELETED:
        return False
    if filters.memory_type is not None and memory.memory_type != filters.memory_type:
        return False
    if filters.project_id is not None and memory.project_id != filters.project_id:
        return False
    if filters.scope is not None and memory.scope != filters.scope:
        return False
    if (
        filters.embedding_model is not None
        and memory.embedding_model != filters.embedding_model
    ):
        return False
    if (
        filters.embedding_version is not None
        and memory.embedding_version != filters.embedding_version
    ):
        return False
    if filters.exclude_superseded and memory.superseded_by_memory_id is not None:
        return False

    reference = _as_utc(now or datetime.now(timezone.utc))
    if memory.valid_from is not None and reference < _as_utc(memory.valid_from):
        return False
    if memory.valid_until is not None and reference > _as_utc(memory.valid_until):
        return False
    return True
