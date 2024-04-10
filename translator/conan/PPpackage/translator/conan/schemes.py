from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass


class Parameters(BaseModel):
    pass


@pydantic_dataclass
class Requirement:
    package: str
    version: str
