from pydantic import BaseModel, Field


class Scratchpad(BaseModel):
    observations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    hypothesis: str | None = None
