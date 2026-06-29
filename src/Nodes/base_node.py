from abc import ABC, abstractmethod

from Core import ExecutionContext, BasePromptBuilder
from Types import NodeResult
from llm import BaseLLMClient
class BaseNode(ABC):

  def __init__(self, llm: BaseLLMClient, promptBuilder: BasePromptBuilder) -> None:
    self.llm = llm
    self.promptBuilder = promptBuilder

  @abstractmethod
  def run(self,context:ExecutionContext)->NodeResult:
    pass

