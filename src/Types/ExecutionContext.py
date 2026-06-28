from pydantic import BaseModel
from Types.TaskExecution import TaskExecution
from Types.Goal import Goal
from Types.Scratchpad import Scratchpad
from Types.Plan import Plan
class ExecutionContext(BaseModel):
  goal: Goal
  plans:Plan
  current_task_execution: TaskExecution | None = None
  scratchpad: Scratchpad | None = None


