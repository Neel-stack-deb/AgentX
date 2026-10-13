from datetime import datetime, timedelta, timezone

from Memory.eligibility import is_memory_eligible
from Memory.retrieval import MemoryRetrievalFilter
from Types.Memory import Memory, MemoryStatus, MemoryType


def _memory(**kwargs) -> Memory:
    defaults = {
        "content": "sample",
        "status": MemoryStatus.ACTIVE,
        "project_id": "p1",
        "scope": "team-a",
    }
    defaults.update(kwargs)
    return Memory(**defaults)


def test_scope_and_project_hard_filter():
    memory = _memory(project_id="other")
    filters = MemoryRetrievalFilter(project_id="p1", scope="team-a")
    assert not is_memory_eligible(memory, filters)


def test_superseded_excluded():
    memory = _memory(superseded_by_memory_id="replacement-id")
    filters = MemoryRetrievalFilter()
    assert not is_memory_eligible(memory, filters)


def test_validity_window_inclusive_bounds():
    now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    memory = _memory(
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
    )
    assert is_memory_eligible(memory, MemoryRetrievalFilter(), now=now)


def test_expired_memory_excluded():
    now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    memory = _memory(valid_until=now - timedelta(seconds=1))
    assert not is_memory_eligible(memory, MemoryRetrievalFilter(), now=now)


def test_not_yet_valid_excluded():
    now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    memory = _memory(valid_from=now + timedelta(hours=1))
    assert not is_memory_eligible(memory, MemoryRetrievalFilter(), now=now)
