from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from PPpackage.utils.json.validator import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    mirrorlist: list[Annotated[str, WithVariables]]
    database_path: Annotated[Path, WithVariables] | None = None
    repository: Annotated[str, WithVariables] | None = None
