from enum import Enum

class PlanStepStatus(str, Enum):
  PENDING = "pending"
  COMPLETED = "completed"
  IN_PROGRESS = "in_progress" #required so that multiple nodes do not execute the same step
  FAILED = "failed"

class ExecutionStatus(str, Enum):
  RUNNING = "running"
  COMPLETED = "completed"
  FAILED = "falied"
  
class PromptTemplate(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    REFLECTOR = "reflector"