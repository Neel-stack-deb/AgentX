from pydantic import BaseModel, Field


class Goal(BaseModel):
    description: str
    constraints: list[str] = Field(default_factory=list)
