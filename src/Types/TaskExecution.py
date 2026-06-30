from pydantic import BaseModel
from Types.ExecutionResponse import ExecutionResponse
from Types.Reflection import Reflection


class TaskExecution(BaseModel):
    step_id: str
    current_response: ExecutionResponse | None = None
    current_reflection: Reflection | None = None
