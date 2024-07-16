from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from pydantic import AnyUrl, BaseModel

from PPpackage.utils.json.validator import WithVariables


class DriverParameters(BaseModel):
    pass


class RepositoryParameters(BaseModel):
    database_path: Annotated[Path, WithVariables] | None = None
    url: AnyUrl
    verify_ssl: bool = True


type ConanOptions = Mapping[str, str]
type ConanSettings = Mapping[str, str]


class Options(BaseModel):
    options: ConanOptions
    settings: ConanSettings


class ConanProductInfo(BaseModel):
    version: str
    revision: str
    package_id: str
