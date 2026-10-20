"""In-memory store for hierarchical memory summaries."""

from __future__ import annotations

from abc import ABC, abstractmethod

from Types.HierarchicalMemory import MemorySummary, SummaryScopeType, SummaryStatus


class HierarchicalSummaryStore(ABC):
    @abstractmethod
    def create(self, summary: MemorySummary) -> MemorySummary:
        ...

    @abstractmethod
    def get(self, summary_id: str) -> MemorySummary | None:
        ...

    @abstractmethod
    def get_current_summary(
        self, scope_type: SummaryScopeType, scope_id: str
    ) -> MemorySummary | None:
        """Latest ACTIVE summary for the scope (excludes stale and superseded)."""
        ...

    @abstractmethod
    def list_by_parent(self, parent_summary_id: str) -> list[MemorySummary]:
        ...

    @abstractmethod
    def mark_stale_for_memory(self, memory_id: str) -> list[MemorySummary]:
        ...

    @abstractmethod
    def regenerate(self, summary_id: str, new_content: str) -> MemorySummary:
        ...


class InMemoryHierarchicalSummaryStore(HierarchicalSummaryStore):
    def __init__(self) -> None:
        self._summaries: dict[str, MemorySummary] = {}

    def create(self, summary: MemorySummary) -> MemorySummary:
        self._summaries[summary.summary_id] = summary
        return summary

    def get(self, summary_id: str) -> MemorySummary | None:
        return self._summaries.get(summary_id)

    def _update(self, summary: MemorySummary) -> MemorySummary:
        self._summaries[summary.summary_id] = summary
        return summary

    def get_current_summary(
        self, scope_type: SummaryScopeType, scope_id: str
    ) -> MemorySummary | None:
        candidates = [
            s
            for s in self._summaries.values()
            if s.scope_type == scope_type
            and s.scope_id == scope_id
            and s.status == SummaryStatus.ACTIVE
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.version)

    def list_by_parent(self, parent_summary_id: str) -> list[MemorySummary]:
        return sorted(
            [
                s
                for s in self._summaries.values()
                if s.parent_summary_id == parent_summary_id
                and s.status == SummaryStatus.ACTIVE
            ],
            key=lambda s: (s.scope_type.value, s.scope_id),
        )

    def mark_stale_for_memory(self, memory_id: str) -> list[MemorySummary]:
        updated: list[MemorySummary] = []
        for summary in self._summaries.values():
            if memory_id not in summary.source_memory_ids:
                continue
            if summary.status != SummaryStatus.ACTIVE:
                continue
            updated.append(
                self._update(
                    summary.model_copy(update={"status": SummaryStatus.STALE})
                )
            )
        return updated

    def regenerate(self, summary_id: str, new_content: str) -> MemorySummary:
        existing = self.get(summary_id)
        if existing is None:
            raise KeyError(f"summary not found: {summary_id}")
        self._update(
            existing.model_copy(update={"status": SummaryStatus.SUPERSEDED})
        )
        replacement = MemorySummary(
            scope_type=existing.scope_type,
            scope_id=existing.scope_id,
            parent_summary_id=existing.parent_summary_id,
            content=new_content,
            source_memory_ids=list(existing.source_memory_ids),
            version=existing.version + 1,
            status=SummaryStatus.ACTIVE,
            supersedes_summary_id=existing.summary_id,
        )
        return self.create(replacement)
