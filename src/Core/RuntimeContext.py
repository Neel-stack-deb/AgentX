from pydantic import BaseModel
from Types.Enums import ExecutionStatus
class ExecutionContext(BaseModel):
  execution_id: str
  current_node: str
  retry_count: int
  execution_status: ExecutionStatus