from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from Types.HistoryRecord import HistoryRecord

if TYPE_CHECKING:
    from Core.ExecutionContext import ExecutionContext


class NodeResult(BaseModel):
    def build_history(
        self, execution_id: str, context: ExecutionContext
    ) -> HistoryRecord:
        pass
