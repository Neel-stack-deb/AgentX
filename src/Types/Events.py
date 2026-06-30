import datetime
from pydantic import BaseModel


class Event(BaseModel):
    execution_id: str
    timestamp: datetime


class GoalReceived(Event):
    artifact_id: str


class PlanCreated(Event):
    artifact_id: str


class TaskStarted(Event):
    step_id: int


class TaskCompleted(Event):
    step_id: int
    artifact_id: str


class ReflectionCompleted(Event):
    step_id: int
    artifact_id: str


class ExecutionFinished(Event):
    success: bool
