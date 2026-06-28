from pydantic import BaseModel

from Types.Artifact import Artifact
from Types.Events import Event
class History(BaseModel):
  artifacts:list[Artifact]
  events: list[Event]