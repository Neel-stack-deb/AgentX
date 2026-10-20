"""Deterministic hierarchical retrieval over summaries and source memories."""

from __future__ import annotations

from Memory.hierarchical.summary_store import HierarchicalSummaryStore
from Memory.memory_store import MemoryStore
from Types.HierarchicalMemory import (
    HierarchicalRetrievalIntent,
    HierarchicalRetrievalResult,
    SummaryScopeType,
)


class HierarchicalMemoryRetriever:
    def __init__(
        self,
        summary_store: HierarchicalSummaryStore,
        memory_store: MemoryStore,
    ) -> None:
        self._summaries = summary_store
        self._memories = memory_store

    def retrieve(
        self,
        intent: HierarchicalRetrievalIntent,
        *,
        scope_type: SummaryScopeType,
        scope_id: str,
        topic_scope_id: str | None = None,
    ) -> HierarchicalRetrievalResult:
        if intent == HierarchicalRetrievalIntent.OVERVIEW:
            summary = self._summaries.get_current_summary(scope_type, scope_id)
            if summary is None:
                return HierarchicalRetrievalResult(
                    intent=intent,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    insufficient_evidence=True,
                    message="No current overview summary for scope.",
                )
            return HierarchicalRetrievalResult(
                intent=intent,
                scope_type=scope_type,
                scope_id=scope_id,
                summary=summary,
            )

        if intent == HierarchicalRetrievalIntent.TOPIC:
            topic_id = topic_scope_id or scope_id
            summary = self._summaries.get_current_summary(
                SummaryScopeType.TOPIC, topic_id
            )
            if summary is None:
                return HierarchicalRetrievalResult(
                    intent=intent,
                    scope_type=SummaryScopeType.TOPIC,
                    scope_id=topic_id,
                    insufficient_evidence=True,
                    message="No current topic summary for scope.",
                )
            return HierarchicalRetrievalResult(
                intent=intent,
                scope_type=SummaryScopeType.TOPIC,
                scope_id=topic_id,
                summary=summary,
            )

        # DETAIL: resolve from topic or project summary source memories
        anchor = self._summaries.get_current_summary(scope_type, scope_id)
        if anchor is None and topic_scope_id is not None:
            anchor = self._summaries.get_current_summary(
                SummaryScopeType.TOPIC, topic_scope_id
            )
        if anchor is None or not anchor.source_memory_ids:
            return HierarchicalRetrievalResult(
                intent=intent,
                scope_type=scope_type,
                scope_id=scope_id,
                insufficient_evidence=True,
                message="No summary with source memories to descend from.",
            )

        detailed: list = []
        for memory_id in anchor.source_memory_ids:
            memory = self._memories.get(memory_id)
            if memory is not None:
                detailed.append(memory)

        if not detailed:
            return HierarchicalRetrievalResult(
                intent=intent,
                scope_type=scope_type,
                scope_id=scope_id,
                summary=anchor,
                insufficient_evidence=True,
                message="Source memory ids are missing from the memory store.",
            )

        return HierarchicalRetrievalResult(
            intent=intent,
            scope_type=scope_type,
            scope_id=scope_id,
            summary=anchor,
            detailed_memories=detailed,
        )
