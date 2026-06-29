from abc import ABC, abstractmethod

class BaseNode(ABC):

  def __init__(self, nodeName, nodeDescription) -> None:
    self.nodeName = nodeName
    self.nodeDescription = nodeDescription

  @abstractmethod
  def run(self,*args,**kwargs):
    pass

