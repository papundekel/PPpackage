from pathlib import Path
from typing import Annotated

from pydantic import AnyUrl, BaseModel

from PPpackage.utils.validation import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    cache_path: Annotated[Path, WithVariables]
    url: AnyUrl
    verify_ssl: bool
