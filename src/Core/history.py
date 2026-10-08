from pydantic import BaseModel, Field

from Types.Artifact import Artifact
from Types.Events import Event


class History(BaseModel):
    artifacts: list[Artifact] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)

    def add_event(self, event: Event) -> bool:
        self.events.append(event)
        return True

    def add_artifact(self, artifact: Artifact) -> bool:
        self.artifacts.append(artifact)
        return True
