from abc import ABC, abstractmethod

from Core import ExecutionContext, PromptBuilder
from Types import NodeResult
from llm import LLMClient
class BaseNode(ABC):

  def __init__(self, llm: LLMClient, promptBuilder: PromptBuilder) -> None:
    self.llm = llm
    self.promptBuilder = promptBuilder

  @abstractmethod
  def run(self,context:ExecutionContext)->NodeResult:
    pass

