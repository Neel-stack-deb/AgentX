from Core.ExecutionContext import ExecutionContext
from Nodes.base_node import BaseNode
from Types.Reflection import Reflection
from Types.ReflectorResult import ReflectorResult
from Types.Enums import PromptTemplate


class Reflector(BaseNode):
    async def run(self, context: ExecutionContext) -> ReflectorResult:
        prompt = self.promptBuilder.build(
            context=context, template=PromptTemplate.REFLECTOR
        )

        reflection = await self.llm.generate(prompt, output_mode=Reflection)

        return ReflectorResult(reflection=reflection)
