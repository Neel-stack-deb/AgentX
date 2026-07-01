from pydantic import BaseModel
from Core.RuntimeContext import RuntimeContext
from Core.ExecutionContext import ExecutionContext
from Core.history import History

class OrchestratorOutput(BaseModel):
    runtime: RuntimeContext
    history: History
    context: ExecutionContext