from unittest.mock import AsyncMock, MagicMock

import pytest

from Core.ExecutionContext import ExecutionContext
from Core.ExecutionContextManager import ExecutionContextManager
from Core.Orchestrator import Orchestrator
from Core.RuntimeContext import RuntimeContext
from Core.history import History
from Memory.embedding_provider import HashEmbeddingProvider
from Memory.memory_manager import MemoryManager
from Types.Goal import Goal
from Types.Scratchpad import Scratchpad


from Types.Enums import PlanStepStatus
from Types.Plan import Plan, PlanStep


@pytest.mark.asyncio
async def test_orchestrator_retrieves_memories_before_planning():
    memory_manager = MemoryManager(embedding_provider=HashEmbeddingProvider())
    memory_manager.remember("Always validate immutable context updates.")

    context_manager = ExecutionContextManager()
    captured_contexts: list[ExecutionContext] = []

    completed_plan = Plan(
        steps=[
            PlanStep(
                step_id="1",
                description="done",
                status=PlanStepStatus.COMPLETED,
            )
        ]
    )

    async def fake_run(node, context, runtime, history):
        captured_contexts.append(context)
        if context.plan is None:
            return context.model_copy(update={"plan": completed_plan})
        return context

    node_runner = MagicMock()
    node_runner.run = AsyncMock(side_effect=fake_run)

    orchestrator = Orchestrator(
        planner=MagicMock(),
        executor=MagicMock(),
        reflector=MagicMock(),
        execution_context_manager=context_manager,
        node_runner=node_runner,
        memory_manager=memory_manager,
        memory_top_k=3,
    )

    goal = Goal(description="validate immutable context")
    await orchestrator.execute(goal)

    assert captured_contexts
    first_context = captured_contexts[0]
    assert len(first_context.retrieved_memories) >= 1
    assert any(
        "immutable context" in memory.content.lower()
        for memory in first_context.retrieved_memories
    )
