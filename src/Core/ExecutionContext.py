from pydantic import BaseModel, Field
from Types.TaskExecution import TaskExecution
from Types.Goal import Goal
from Types.Scratchpad import Scratchpad
from Types.Plan import Plan
from Types.Memory import Memory


class ExecutionContext(BaseModel):
    goal: Goal
    plan: Plan | None = None
    current_task_execution: TaskExecution | None = None
    scratchpad: Scratchpad | None = None
    retrieved_memories: list[Memory] = Field(default_factory=list)
