from collections.abc import Mapping
from typing import Any

from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass(frozen=True)
class Package:
    namespace: str
    name: str


@pydantic_dataclass(frozen=True)
class VariableToPackageVersionMapping:
    variable: str
    package: Package
    version: str


@pydantic_dataclass(frozen=True)
class ResolutionLiteral:
    is_true: bool
    variable: str


Parameters = Mapping[str, Any]


@pydantic_dataclass(frozen=True)
class BaseModuleConfig:
    package: str
    parameters: Parameters = {}


@pydantic_dataclass(frozen=True)
class RepositoryDriverConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class RepositoryConfig:
    driver: RepositoryDriverConfig
    parameters: Parameters = {}
