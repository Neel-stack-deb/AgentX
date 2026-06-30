from pydantic import BaseModel

from llm.BaseLLMClient import BaseLLMClient

from Types.Plan import Plan, PlanStep
from Types.Enums import PlanStepStatus

from Types.ExecutionResponse import ExecutionResponse
from Types.Reflection import Reflection


class MockLLMClient(BaseLLMClient):

    async def generate(self, prompt: str, output_model: type[BaseModel]) -> BaseModel:

        if output_model == Plan:

            return Plan(
                steps=[
                    PlanStep(
                        step_id=1,
                        description="Research the problem",
                        status=PlanStepStatus.PENDING,
                    ),
                    PlanStep(
                        step_id=2,
                        description="Implement the solution",
                        status=PlanStepStatus.PENDING,
                    ),
                ]
            )

        if output_model == ExecutionResponse:

            return ExecutionResponse(content="Task completed successfully.")

        if output_model == Reflection:

            return Reflection(content="Execution looks correct.")

        raise ValueError(f"Unsupported output model: {output_model}")
