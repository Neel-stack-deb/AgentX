from pydantic import BaseModel

from Types.Enums import ReflectionDecision


class Reflection(BaseModel):
    decision: ReflectionDecision
    content: str
