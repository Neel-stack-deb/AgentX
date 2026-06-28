import datetime
from pydantic import BaseModel

class Event(BaseModel):
  execution_id: str
  timestamp: datetime

class GoalReceived(Event):
    pass


class PlanCreated(Event):
    pass


class TaskStarted(Event):
    step_id: int


class TaskCompleted(Event):
    step_id: int


class ReflectionCompleted(Event):
    step_id: int


class ExecutionFinished(Event):
    success: bool