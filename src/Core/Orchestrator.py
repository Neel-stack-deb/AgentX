from Nodes.Planner import Planner
from Nodes.Executer import Executer
from Nodes.Reflector import Reflector

from Core.NodeRunner import NodeRunner
from Core.ExecutionContextManager import ExecutionContextManager

from Types.OrchestratorOutput import OrchestratorOutput
from Types.Goal import Goal
from Core.history import History
from Core.RuntimeContext import RuntimeContext
from Types.Enums import ExecutionStatus
from Memory.memory_manager import MemoryManager


class Orchestrator:

    def __init__(
        self,
        planner: Planner,
        executor: Executer,
        reflector: Reflector,
        execution_context_manager: ExecutionContextManager,
        node_runner: NodeRunner,
        memory_manager: MemoryManager | None = None,
        memory_top_k: int = 5,
    ):
        self.planner = planner
        self.executor = executor
        self.reflector = reflector
        self.context_manager = execution_context_manager
        self.node_runner = node_runner
        self.memory_manager = memory_manager
        self.memory_top_k = memory_top_k

    async def execute(
        self,
        goal: Goal,
    ):

        runtime = RuntimeContext(
            status=ExecutionStatus.CREATED,
        )

        history = History()

        context = self.context_manager.initialize(goal)

        if self.memory_manager is not None:
            memories = self.memory_manager.retrieve(
                query=goal.description,
                top_k=self.memory_top_k,
            )
            context = self.context_manager.with_retrieved_memories(
                context=context,
                memories=memories,
            )

        runtime.status = ExecutionStatus.RUNNING

        # -----------------------------
        # Planning Phase
        # -----------------------------
        runtime.current_node = "planner"

        context = await self.node_runner.run(
            node=self.planner,
            context=context,
            runtime=runtime,
            history=history,
        )

        # -----------------------------
        # Execution Loop
        # -----------------------------
        while not context.plan.is_completed():

            runtime.current_node = "executor"

            context = await self.node_runner.run(
                node=self.executor,
                context=context,
                runtime=runtime,
                history=history,
            )

            runtime.current_node = "reflector"

            context = await self.node_runner.run(
                node=self.reflector,
                context=context,
                runtime=runtime,
                history=history,
            )

        runtime.current_node = None
        runtime.status = ExecutionStatus.FINISHED

        return OrchestratorOutput(
            runtime=runtime,
            history=history,
            context=context,
        )