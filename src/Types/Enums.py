from enum import Enum


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"  # required so that multiple nodes do not execute the same step
    FAILED = "failed"


class ExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class PromptTemplate(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    REFLECTOR = "reflector"


class ReflectionDecision(str, Enum):
    APPROVED = "approved"
    RETRY = "retry"
    REPLAN = "replan"
