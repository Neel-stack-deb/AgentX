from pydantic import BaseModel

class Goal(BaseModel):
  description: str
  constraints: list[str]

