from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from PPpackage.utils.validation import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    database_path: Annotated[Path, WithVariables]
    repository: str
    mirrorlist: list[str]
