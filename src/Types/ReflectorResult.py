from Types.NodeResult import NodeResult
from Types.Reflection import Reflection
from Types.HistoryRecord import HistoryRecord
from Types.Events import ReflectionCompleted
from Core.ExecutionContext import ExecutionContext

class ReflectorResult(NodeResult):
    reflection: Reflection
    def build_history(
    self,
    execution_id: str,
    context: ExecutionContext,
    ) -> HistoryRecord:

        event = ReflectionCompleted(
            execution_id=execution_id,
            step_id=context.current_task_execution.step_id,
            artifact_id=context.current_task_execution.artifact_id,
        )

        return HistoryRecord(
            event=event,
            artifact=None,
        )