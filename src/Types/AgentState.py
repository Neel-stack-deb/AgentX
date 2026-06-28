from pydantic import BaseModel
from Types import CurrentExecutionContext
from Types.Goal import Goal
from Types.Scratchpad import Scratchpad
from Types.Plan import Plan
class AgentState(BaseModel):
  goal: Goal
  plans:list[Plan]
  current_execution_context: CurrentExecutionContext | None = None
  scratchpad: Scratchpad | None = None


