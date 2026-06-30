from Core import ExecutionContext
from Nodes.base_node import BaseNode
from Types import Plan, PlannerResult
from Types.Enums import PromptTemplate


class Planner(BaseNode):
    async def run(self, context: ExecutionContext) -> PlannerResult:
        prompt = self.promptBuilder.build(
            context=context, template=PromptTemplate.PLANNER
        )
        plan = await self.llm.generate(prompt, output_model=Plan)
        return PlannerResult(plan=plan)
