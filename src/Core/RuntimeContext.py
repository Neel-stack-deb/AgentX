from pydantic import BaseModel, Field
from uuid import uuid4
from Types.Enums import ExecutionStatus


class RuntimeContext(BaseModel):
    #TODO: uuid indexing
    execution_id: str = Field(
        default_factory=lambda: str(uuid4())
    )  # to reference the metrics or debugging an execution when concurrent executions will happen
    current_node: str | None = None
    retry_count: int = 0
    status: ExecutionStatus = ExecutionStatus.CREATED
