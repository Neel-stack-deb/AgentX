from pydantic import BaseModel

class Scratchpad(BaseModel):
  observations: list[str]
  next_steps: list[str]
  hypothesis: str | None = None