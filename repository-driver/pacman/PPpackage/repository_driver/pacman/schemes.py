from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from PPpackage.utils.json.validator import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    database_path: Annotated[Path, WithVariables]
    mirrorlist: list[Annotated[str, WithVariables]]
    repository: Annotated[str, WithVariables] | None = None
