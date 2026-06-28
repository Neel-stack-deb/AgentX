from pydantic import BaseModel
from Types.Response import Response
from Types.Reflection import Reflection
class CurrentExecutionContext(BaseModel):
  current_response: Response | None = None
  current_reflection: Reflection | None = None