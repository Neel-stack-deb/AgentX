from Core import ExecutionContext
from Nodes.base_node import BaseNode
from Types import ExecuterResult, ExecutionResponse
from Types.Enums import PromptTemplate


class Executer(BaseNode):
    async def run(self, context: ExecutionContext) -> ExecuterResult:
        prompt = self.promptBuilder.build(
            context=context, template=PromptTemplate.EXECUTOR
        )

        executionResponse = await self.llm.generate(
            prompt, output_model=ExecutionResponse
        )

        return ExecuterResult(executionResponse=executionResponse)
