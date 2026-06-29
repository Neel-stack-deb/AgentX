from Core.BasePromptBuilder import BasePromptBuilder

from Core.ExecutionContext import ExecutionContext
from Types.Enums import PromptTemplate


class PromptBuilder(BasePromptBuilder):

    def build(self, template: PromptTemplate, context: ExecutionContext) -> str:

        if template == PromptTemplate.PLANNER:
            return self._build_planner_prompt(context)

        if template == PromptTemplate.EXECUTOR:
            return self._build_executor_prompt(context)

        if template == PromptTemplate.REFLECTOR:
            return self._build_reflector_prompt(context)

        raise ValueError(f"Unknown template: {template}")

    def _build_planner_prompt(self, context: ExecutionContext) -> str:

        return f"""
You are an expert planner.

Goal:
{context.goal.description}

Generate a step-by-step plan.
"""

    def _build_executor_prompt(self, context: ExecutionContext) -> str:

        step = context.plan.next_pending_step()
        # TODO: handling the None case

        return f"""
Execute the following step.

Goal:
{context.goal.description}

Current Step:
{step.description}
"""

    def _build_reflector_prompt(self, context: ExecutionContext) -> str:

        return f"""
Review the following execution.

Response:

{context.current_task_execution.current_response.content}
"""
