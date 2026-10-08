from Core.ExecutionContext import ExecutionContext
from Nodes.base_node import BaseNode
from Types.ExecuterResult import ExecuterResult
from Types.ExecutionResponse import ExecutionResponse
from Types.Enums import PromptTemplate


class Executer(BaseNode):
    async def run(self, context: ExecutionContext) -> ExecuterResult:
        prompt = self.promptBuilder.build(
            context=context, template=PromptTemplate.EXECUTOR
        )

        executionResponse = await self.llm.generate(
            prompt, output_model=ExecutionResponse
        )

        return ExecuterResult(
            executionResponse=executionResponse)
