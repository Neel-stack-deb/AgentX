import datetime
from pydantic import BaseModel

from Types import ExecutionResponse, Plan, Reflection


class Artifact(BaseModel):
    artifact_id: str
    execution_id: str
    created_at: datetime


class PlanArtifact(Artifact):
    plan: Plan


class ExecutionArtifact(Artifact):
    step_id: str
    response: ExecutionResponse
    reflection: Reflection | None

