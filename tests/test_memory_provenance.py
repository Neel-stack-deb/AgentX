from Memory.embedding_provider import HashEmbeddingProvider
from Memory.hierarchical import InMemoryHierarchicalSummaryStore
from Memory.memory_manager import MemoryManager
from Types.HierarchicalMemory import MemorySummary, SummaryScopeType, SummaryStatus


def test_memory_update_marks_dependent_summaries_stale():
    provider = HashEmbeddingProvider(dimensions=32)
    summaries = InMemoryHierarchicalSummaryStore()
    manager = MemoryManager(
        embedding_provider=provider,
        summary_store=summaries,
    )
    memory = manager.remember("Initial durable fact.")
    summaries.create(
        MemorySummary(
            scope_type=SummaryScopeType.TOPIC,
            scope_id="facts",
            content="Summary of the fact.",
            source_memory_ids=[memory.memory_id],
        )
    )
    assert (
        summaries.get_current_summary(SummaryScopeType.TOPIC, "facts") is not None
    )

    summary_id = summaries.get_current_summary(
        SummaryScopeType.TOPIC, "facts"
    ).summary_id
    manager.touch_content(memory.memory_id, "Updated durable fact.")
    assert summaries.get_current_summary(SummaryScopeType.TOPIC, "facts") is None
    assert summaries.get(summary_id).status == SummaryStatus.STALE


def test_explicit_invalidation_without_content_change():
    provider = HashEmbeddingProvider(dimensions=32)
    summaries = InMemoryHierarchicalSummaryStore()
    manager = MemoryManager(
        embedding_provider=provider,
        summary_store=summaries,
    )
    memory = manager.remember("Another fact.")
    summary = summaries.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="Overview.",
            source_memory_ids=[memory.memory_id],
        )
    )

    invalidated = manager.invalidate_dependent_summaries(memory.memory_id)
    assert len(invalidated) == 1
    assert invalidated[0].summary_id == summary.summary_id
    assert summaries.get(summary.summary_id).status == SummaryStatus.STALE


def test_regenerate_summary_creates_new_version():
    provider = HashEmbeddingProvider(dimensions=32)
    summaries = InMemoryHierarchicalSummaryStore()
    manager = MemoryManager(
        embedding_provider=provider,
        summary_store=summaries,
    )
    original = summaries.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="v1",
            source_memory_ids=["m1"],
        )
    )
    replacement = manager.regenerate_summary(original.summary_id, "v2")
    assert replacement.version == 2
    assert summaries.get(original.summary_id).status == SummaryStatus.SUPERSEDED
    current = summaries.get_current_summary(SummaryScopeType.GLOBAL, "agentx")
    assert current is not None
    assert current.summary_id == replacement.summary_id
