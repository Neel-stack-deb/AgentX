from datetime import datetime, timezone

import pytest

from Core.ExecutionContext import ExecutionContext
from Core.ExecutionContextManager import ExecutionContextManager
from Core.PromptBuilder import PromptBuilder
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.memory_manager import MemoryManager
from Memory.vector_math import cosine_similarity
from Memory.vector_store import InMemoryVectorStore
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
        store.upsert(memory_id, embedding_provider.embed(text))

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
