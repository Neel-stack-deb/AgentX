from datetime import datetime, timezone

import pytest

from Core.ExecutionContext import ExecutionContext
from Core.ExecutionContextManager import ExecutionContextManager
from Core.PromptBuilder import PromptBuilder
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.memory_manager import MemoryManager
from Memory.retrieval import MemoryRetrievalFilter, VectorIndexMetadata, VectorIndexRecord
from Memory.vector_math import cosine_similarity
from Memory.vector_store import BruteForceVectorStore, InMemoryVectorStore, VectorSearchStrategy
from Types.Enums import PromptTemplate
from Types.Goal import Goal
from Types.Memory import Memory, MemoryStatus, MemoryType
from Types.Scratchpad import Scratchpad


@pytest.fixture
def embedding_provider() -> HashEmbeddingProvider:
    return HashEmbeddingProvider(dimensions=32)


@pytest.fixture
def memory_manager(embedding_provider: HashEmbeddingProvider) -> MemoryManager:
    return MemoryManager(embedding_provider=embedding_provider)


def test_memory_creation_defaults():
    memory = Memory(content="AgentX uses immutable execution context.")
    assert memory.memory_id
    assert memory.memory_type == MemoryType.SEMANTIC
    assert memory.status == MemoryStatus.ACTIVE
    assert memory.created_at.tzinfo is not None


def test_embedding_provider_produces_normalized_vectors(
    embedding_provider: HashEmbeddingProvider,
):
    vector = embedding_provider.embed("vector memory retrieval")
    assert len(vector) == embedding_provider.dimensions
    norm = sum(value * value for value in vector) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-5) or norm == 0.0


def test_cosine_similarity_orders_related_text(embedding_provider: HashEmbeddingProvider):
    a = embedding_provider.embed("python vector memory search")
    b = embedding_provider.embed("python vector memory indexing")
    c = embedding_provider.embed("completely unrelated cooking recipe")
    assert cosine_similarity(a, b) > cosine_similarity(a, c)


def test_vector_store_top_k(embedding_provider: HashEmbeddingProvider):
    store = InMemoryVectorStore()
    ids = ["a", "b", "c"]
    texts = [
        "deploy agent orchestrator",
        "deploy agent memory",
        "bake sourdough bread",
    ]
    for memory_id, text in zip(ids, texts):
        store.upsert(
            VectorIndexRecord(
                memory_id=memory_id,
                embedding=embedding_provider.embed(text),
                metadata=VectorIndexMetadata(
                    embedding_model=embedding_provider.model_name,
                    embedding_version=embedding_provider.model_version,
                    embedding_dimension=embedding_provider.dimensions,
                ),
            )
        )

    results = store.similarity_search(
        query_embedding=embedding_provider.embed("agent memory orchestrator"),
        top_k=2,
    )
    assert len(results) == 2
    assert results[0][0] in {"a", "b"}


def test_memory_manager_remember_and_retrieve(memory_manager: MemoryManager):
    memory_manager.remember("User prefers concise plans.")
    memory_manager.remember("Previous run failed on step validation.")
    memory_manager.remember("Favorite color is blue.")

    hits = memory_manager.retrieve("concise planning preference", top_k=2)
    assert len(hits) >= 1
    assert any("concise" in hit.content for hit in hits)


def test_memory_manager_update_reindexes(memory_manager: MemoryManager):
    memory = memory_manager.remember("initial topic about cats")
    memory_manager.touch_content(memory.memory_id, "updated topic about dogs")

    hits = memory_manager.retrieve("dogs and pets", top_k=1)
    assert hits[0].content == "updated topic about dogs"


def test_memory_manager_delete_excludes_from_retrieval(memory_manager: MemoryManager):
    memory = memory_manager.remember("secret token alpha")
    memory_manager.delete(memory.memory_id)
    hits = memory_manager.retrieve("secret token alpha", top_k=3)
    assert all(hit.memory_id != memory.memory_id for hit in hits)


def test_execution_context_manager_with_retrieved_memories_is_immutable():
    manager = ExecutionContextManager()
    original = ExecutionContext(
        goal=Goal(description="Ship vector memory"),
        scratchpad=Scratchpad(),
    )
    memories = [
        Memory(content="Past success with pydantic models"),
        Memory(content="Keep history separate from memory"),
    ]

    updated = manager.with_retrieved_memories(original, memories)

    assert original.retrieved_memories == []
    assert len(updated.retrieved_memories) == 2
    assert updated is not original


def test_brute_force_store_declares_strategy(embedding_provider: HashEmbeddingProvider):
    store = InMemoryVectorStore()
    assert store.search_strategy == VectorSearchStrategy.BRUTE_FORCE


def test_metadata_filtering_by_project(memory_manager: MemoryManager):
    memory_manager.remember("alpha deployment notes", project_id="proj-a")
    memory_manager.remember("beta deployment notes", project_id="proj-b")

    hits = memory_manager.retrieve(
        "deployment notes",
        top_k=5,
        filters=MemoryRetrievalFilter(project_id="proj-a"),
    )
    assert len(hits) == 1
    assert hits[0].project_id == "proj-a"


def test_metadata_filtering_by_memory_type(memory_manager: MemoryManager):
    memory_manager.remember("how to run tests", memory_type=MemoryType.PROCEDURAL)
    memory_manager.remember("user likes dark mode", memory_type=MemoryType.SEMANTIC)

    hits = memory_manager.retrieve(
        "tests",
        top_k=5,
        filters=MemoryRetrievalFilter(memory_type=MemoryType.PROCEDURAL),
    )
    assert len(hits) == 1
    assert hits[0].memory_type == MemoryType.PROCEDURAL


def test_embedding_version_stored_on_remember(embedding_provider: HashEmbeddingProvider):
    manager = MemoryManager(embedding_provider=embedding_provider)
    memory = manager.remember("versioned embedding record")
    assert memory.embedding_model == "hash-bow"
    assert memory.embedding_version == "1"
    assert memory.embedding_dimension == embedding_provider.dimensions


def test_different_embedding_versions_represented():
    v1 = HashEmbeddingProvider(dimensions=32, model_version="1")
    v2 = HashEmbeddingProvider(dimensions=32, model_version="2")
    m1 = MemoryManager(embedding_provider=v1).remember("shared content")
    m2 = MemoryManager(embedding_provider=v2).remember("shared content")
    assert m1.embedding_version == "1"
    assert m2.embedding_version == "2"


def test_vector_store_is_replaceable(embedding_provider: HashEmbeddingProvider):
    class RecordingVectorStore(BruteForceVectorStore):
        def __init__(self) -> None:
            super().__init__()
            self.search_calls: list[tuple[int, MemoryRetrievalFilter | None]] = []

        def similarity_search(self, query_embedding, top_k, filters=None):
            self.search_calls.append((top_k, filters))
            return super().similarity_search(query_embedding, top_k, filters)

    store = RecordingVectorStore()
    manager = MemoryManager(
        embedding_provider=embedding_provider,
        vector_store=store,
    )
    manager.remember("replaceable backend check")
    manager.retrieve("backend", top_k=3, filters=MemoryRetrievalFilter(scope="team-1"))
    assert len(store.search_calls) == 1
    assert store.search_calls[0][0] == 3


def test_superseded_memory_excluded_by_default(memory_manager: MemoryManager):
    old = memory_manager.remember("old API contract")
    new = memory_manager.remember("new API contract")
    memory_manager.supersede(old.memory_id, new.memory_id)

    hits = memory_manager.retrieve("API contract", top_k=5)
    ids = {hit.memory_id for hit in hits}
    assert old.memory_id not in ids
    assert new.memory_id in ids


def test_prompt_builder_includes_retrieved_memories():
    builder = PromptBuilder()
    context = ExecutionContext(
        goal=Goal(description="Plan deployment"),
        retrieved_memories=[
            Memory(content="Use staged rollouts", memory_type=MemoryType.PROCEDURAL),
        ],
    )
    prompt = builder.build(PromptTemplate.PLANNER, context)
    assert "Relevant memories:" in prompt
    assert "staged rollouts" in prompt
