from pydantic import BaseModel
from Types.Enums import ExecutionStatus

class ExecutionContext(BaseModel):
  execution_id: str #to reference the metrics or debugging an execution when concurrent executions will happen
  current_node: str
  retry_count: int
  execution_status: ExecutionStatus