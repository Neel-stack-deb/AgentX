from Memory.embedding_provider import HashEmbeddingProvider
from Memory.hierarchical import (
    HierarchicalMemoryRetriever,
    InMemoryHierarchicalSummaryStore,
)
from Memory.memory_manager import MemoryManager
from Types.HierarchicalMemory import (
    HierarchicalRetrievalIntent,
    MemorySummary,
    SummaryScopeType,
    SummaryStatus,
)


def test_summary_parent_and_source_links():
    store = InMemoryHierarchicalSummaryStore()
    global_summary = store.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="AgentX is a modular agent framework.",
            source_memory_ids=["mem-global"],
        )
    )
    project = store.create(
        MemorySummary(
            scope_type=SummaryScopeType.PROJECT,
            scope_id="memory-module",
            parent_summary_id=global_summary.summary_id,
            content="Module 2 adds vector memory.",
            source_memory_ids=["mem-project"],
        )
    )
    children = store.list_by_parent(global_summary.summary_id)
    assert len(children) == 1
    assert children[0].summary_id == project.summary_id


def test_hierarchical_retrieval_descends_to_detailed_memories():
    provider = HashEmbeddingProvider(dimensions=32)
    manager = MemoryManager(embedding_provider=provider)
    store = InMemoryHierarchicalSummaryStore()
    detail = manager.remember("PostgreSQL stores memory metadata and embeddings.")

    store.create(
        MemorySummary(
            scope_type=SummaryScopeType.TOPIC,
            scope_id="postgres-choice",
            content="We use PostgreSQL for durable memory.",
            source_memory_ids=[detail.memory_id],
        )
    )

    retriever = HierarchicalMemoryRetriever(
        summary_store=store, memory_store=manager._memory_store
    )
    result = retriever.retrieve(
        HierarchicalRetrievalIntent.DETAIL,
        scope_type=SummaryScopeType.TOPIC,
        scope_id="postgres-choice",
    )

    assert not result.insufficient_evidence
    assert len(result.detailed_memories) == 1
    assert result.detailed_memories[0].memory_id == detail.memory_id


def test_stale_and_superseded_summaries_are_not_current():
    store = InMemoryHierarchicalSummaryStore()
    summary = store.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="Version 1 overview.",
            source_memory_ids=["m1"],
        )
    )
    store.mark_stale_for_memory("m1")
    assert store.get_current_summary(SummaryScopeType.GLOBAL, "agentx") is None

    fresh = store.create(
        MemorySummary(
            scope_type=SummaryScopeType.GLOBAL,
            scope_id="agentx",
            content="Version 1b after stale.",
            source_memory_ids=["m1"],
        )
    )
    v2 = store.regenerate(fresh.summary_id, "Version 2 overview.")
    assert v2.version == 2
    assert store.get(fresh.summary_id).status == SummaryStatus.SUPERSEDED
    current = store.get_current_summary(SummaryScopeType.GLOBAL, "agentx")
    assert current is not None
    assert current.summary_id == v2.summary_id
    assert current.content == "Version 2 overview."


def test_insufficient_evidence_when_no_summary():
    provider = HashEmbeddingProvider(dimensions=32)
    manager = MemoryManager(embedding_provider=provider)
    store = InMemoryHierarchicalSummaryStore()
    retriever = HierarchicalMemoryRetriever(
        summary_store=store, memory_store=manager._memory_store
    )
    result = retriever.retrieve(
        HierarchicalRetrievalIntent.OVERVIEW,
        scope_type=SummaryScopeType.PROJECT,
        scope_id="missing",
    )
    assert result.insufficient_evidence
    assert result.summary is None
