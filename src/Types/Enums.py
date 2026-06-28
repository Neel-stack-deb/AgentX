from enum import Enum

class PlanStepStatus(str, Enum):
  PENDING = "pending"
  COMPLETED = "completed"
  IN_PROGRESS = "in_progress" #required so that multiple nodes do not execute the same step
  FAILED = "failed"