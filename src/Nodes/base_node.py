from abc import ABC, abstractmethod

from Core.BasePromptBuilder import BasePromptBuilder
from Core.ExecutionContext import ExecutionContext
from Types.NodeResult import NodeResult
from llm.BaseLLMClient import BaseLLMClient


class BaseNode(ABC):

    def __init__(self, llm: BaseLLMClient, promptBuilder: BasePromptBuilder) -> None:
        self.llm = llm
        self.promptBuilder = promptBuilder

    @abstractmethod
    def run(self, context: ExecutionContext) -> NodeResult:
        pass
