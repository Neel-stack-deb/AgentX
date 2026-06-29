from abc import ABC,abstractmethod

from pydantic import BaseModel

class BaseLLMClient(ABC):
  @abstractmethod
  def generate(
    self,
    prompt: str,
    output_model: type[BaseModel]
  )->BaseModel:
    pass