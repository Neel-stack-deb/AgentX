from pydantic import BaseModel

from Types.Artifact import Artifact
from Types.Events import Event


class HistoryRecord(BaseModel):
    event: Event
    artifact: Artifact | None
