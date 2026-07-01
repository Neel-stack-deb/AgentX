from Types import ExecutionResponse, NodeResult
from Types.Plan import PlanStep
from Types.Artifact import ExecutionArtifact
from Types.Events import TaskCompleted
from Types.HistoryRecord import HistoryRecord
from uuid import uuid4


class ExecutorResult(NodeResult):
    step: PlanStep
    executionResponse: ExecutionResponse

    def build_history(
    self,
    execution_id: str,
    ) -> HistoryRecord:

        artifact = ExecutionArtifact(
            artifact_id=str(uuid4()),
            execution_id=execution_id,
            step_id=self.step.step_id,
            response=self.response,
            reflection=None,
        )

        event = TaskCompleted(
            execution_id=execution_id,
            step_id=self.step.step_id,
            artifact_id=artifact.artifact_id,
        )

        return HistoryRecord(
            event=event,
            artifact=artifact,
        )