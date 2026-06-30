from Core import ExecutionContext
from Nodes.base_node import BaseNode
from Types import Reflection, ReflectorResult
from Types.Enums import PromptTemplate


class Reflector(BaseNode):
    async def run(self, context: ExecutionContext) -> ReflectorResult:
        prompt = self.promptBuilder.build(
            context=context, template=PromptTemplate.REFLECTOR
        )

        reflection = await self.llm.generate(prompt, output_mode=Reflection)

        return ReflectorResult(reflection=reflection)
