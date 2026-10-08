from abc import ABC, abstractmethod
from ast import Pass

from Core.ExecutionContext import ExecutionContext
from Types.Enums import PromptTemplate


class BasePromptBuilder(ABC):
    @abstractmethod
    def build(self, context: ExecutionContext, template: PromptTemplate) -> str:
        pass
