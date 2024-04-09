from collections.abc import Mapping
from typing import Annotated, Any, Literal

from annotated_types import Len
from frozendict import frozendict
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass(frozen=True)
class SimpleRequirement:
    translator: str
    value: Any


@pydantic_dataclass(frozen=True)
class OperatorRequirement:
    operation: Literal["and"] | Literal["or"]
    operands: Annotated[list["Requirements"], Len(1)]


Requirements = SimpleRequirement | OperatorRequirement


@pydantic_dataclass(frozen=True)
class Package:
    namespace: str
    name: str


@pydantic_dataclass(frozen=True)
class PackageVersion(Package):
    version: str
    requirements: Requirements | None


Parameters = Mapping[str, Any]


@pydantic_dataclass(frozen=True)
class BaseModuleConfig:
    package: str
    parameters: Parameters = frozendict()


@pydantic_dataclass(frozen=True)
class RepositoryDriverConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class RepositoryConfig:
    driver: RepositoryDriverConfig
    parameters: Parameters = frozendict()
