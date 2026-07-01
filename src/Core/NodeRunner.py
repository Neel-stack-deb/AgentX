from Nodes.base_node import BaseNode

from Core.ExecutionContextManager import ExecutionContextManager

from Core.ExecutionContext import ExecutionContext
from Core.RuntimeContext import RuntimeContext
from Core.history import History


class NodeRunner:

    def __init__(
        self,
        execution_context_manager: ExecutionContextManager,
    ):
        self.execution_context_manager = execution_context_manager

    async def run(
        self,
        node: BaseNode,
        context: ExecutionContext,
        runtime: RuntimeContext,
        history: History,
    ) -> ExecutionContext:

        # Execute the node
        result = await node.run(context)

        # Record history
        history_record = result.build_history(
            execution_id=runtime.execution_id,
            context=context,
        )

        history.add_event(history_record.event)

        if history_record.artifact is not None:
            history.add_artifact(history_record.artifact)

        # Apply the result to produce a new immutable context
        return self.execution_context_manager.apply(
            context=context,
            result=result,
        )