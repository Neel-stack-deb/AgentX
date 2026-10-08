import datetime
from pydantic import BaseModel, Field


class Event(BaseModel):
    execution_id: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


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
