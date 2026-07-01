from pydantic import BaseModel
from Types.ExecutionResponse import ExecutionResponse
from Types.Plan import PlanStep
from Types.Reflection import Reflection


class TaskExecution(BaseModel):
    artifact_id: str
    step: PlanStep
    current_response: ExecutionResponse | None = None
    current_reflection: Reflection | None = None
