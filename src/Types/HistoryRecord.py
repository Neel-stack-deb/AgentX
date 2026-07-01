from pydantic import BaseModel

from Types import Artifact
from Types.Events import Event


class HistoryRecord(BaseModel):
    event: Event
    artifact: Artifact | None
