from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from PPpackage.utils.json.validator import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    database_path: Annotated[Path, WithVariables] | None = None


class AURPackage(BaseModel):
    Name: str
    Version: str
    Provides: list[str] = []
    Conflicts: list[str] = []
    Depends: list[str] = []
    MakeDepends: list[str] = []
