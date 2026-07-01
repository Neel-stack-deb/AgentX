from pydantic import BaseModel

from Types import HistoryRecord
from Core.ExecutionContext import ExecutionContext

class NodeResult(BaseModel):
    def build_history(self,execution_id: str, context: ExecutionContext) -> HistoryRecord:
        pass
