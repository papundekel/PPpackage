from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

from pydantic import AnyUrl, BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.validation import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    database_path: Annotated[Path, WithVariables]
    url: AnyUrl
    verify_ssl: bool


@pydantic_dataclass
class ConanRequirement:
    package: str
    version: str


ConanOptions = Mapping[str, Any]
