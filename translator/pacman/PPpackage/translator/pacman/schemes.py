from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass


class Parameters(BaseModel):
    pass


@pydantic_dataclass(frozen=True)
class ExcludeRequirement:
    package: str
    exclude: str


@pydantic_dataclass(frozen=True)
class NoProvideRequirement:
    package: str
    no_provide: None
