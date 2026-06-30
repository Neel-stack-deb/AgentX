from pydantic import BaseModel
from Types.Enums import PlanStepStatus


class PlanStep(BaseModel):
    step_id: str  # unique id for the step, this will allow to later refernce the artifacts and the history
    description: str
    status: PlanStepStatus


class Plan(BaseModel):
    steps: list[PlanStep]

    def next_pending_step(self) -> PlanStep | None:
        for step in self.plan_steps:
            if step.status == PlanStepStatus.PENDING:
                return step
        return None

    def is_completed(self) -> bool:
        return all(step.status == PlanStepStatus.COMPLETED for step in self.steps)
