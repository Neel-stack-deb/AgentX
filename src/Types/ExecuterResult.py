from Types import ExecutionResponse, NodeResult
from Types.Plan import PlanStep


class ExecutorResult(NodeResult):
    step: PlanStep
    executionResponse: ExecutionResponse
