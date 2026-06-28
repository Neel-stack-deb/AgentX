from tkinter import constants
from pydantic import BaseModel

class Goal(BaseModel):
  description: str
  constants: list[str]

