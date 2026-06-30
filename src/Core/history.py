from pydantic import BaseModel

from Types.Artifact import Artifact
from Types.Events import Event


class History(BaseModel):
    artifacts: list[Artifact]
    events: list[Event]

    def add_event(self, event: Event) -> bool:
        self.events.append(event)
        return True

    def add_artifact(self, artifact: Artifact) -> bool:
        self.artifacts.append(artifact)
        return True
