from Types import HistoryRecord, NodeResult, Plan
from Types.Artifact import PlanArtifact
from Types.Events import PlanCreated
from uuid import uuid4

class PlannerResult(NodeResult):
    plan: Plan
    def build_history(self, execution_id: str) -> HistoryRecord:
        artifact = PlanArtifact(
            artifact_id=str(uuid4()),
            execution_id=execution_id,
            plan=self.plan,
        )

        event = PlanCreated(
            execution_id=execution_id,
            artifact_id=artifact.artifact_id,
        )

        return HistoryRecord(
            event=event,
            artifact=artifact,
        )
