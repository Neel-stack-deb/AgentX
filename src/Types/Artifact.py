from datetime import datetime
from pydantic import BaseModel, Field

from Types.Plan import Plan
from Types.Reflection import Reflection
from Types.ExecutionResponse import ExecutionResponse


class Artifact(BaseModel):
    artifact_id: str
    execution_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanArtifact(Artifact):
    plan: Plan


class ExecutionArtifact(Artifact):
    step_id: str
    response: ExecutionResponse
    reflection: Reflection | None

