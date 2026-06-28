from pydantic import BaseModel
from Types.Enums import PlanStepStatus
class PlanStep(BaseModel):
  description: str
  status: PlanStepStatus

class Plan(BaseModel):
  plan_steps: list[PlanStep]

  def next_pending_step(self) -> PlanStep:
    for step in self.plan_steps:
      if step.status == PlanStepStatus.PENDING:
        return step


