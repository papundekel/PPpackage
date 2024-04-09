from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from annotated_types import Len
from frozendict import frozendict
from PPpackage.repository_driver.interface.schemes import (
    BaseModuleConfig,
    Package,
    Parameters,
)
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.validation import WithVariables


@pydantic_dataclass(frozen=True)
class SimpleRequirementInput:
    translator: str
    value: Any


@pydantic_dataclass(frozen=True)
class OperatorRequirementInput:
    operation: Literal["and"] | Literal["or"]
    operands: Annotated[list["RequirementInput"], Len(1)]


RequirementInput = SimpleRequirementInput | OperatorRequirementInput


@pydantic_dataclass(frozen=True)
class Input:
    requirements: RequirementInput
    options: Any
    locks: Mapping[str, Mapping[str, str]] = frozendict()
    generators: frozenset[str] | None = None


@pydantic_dataclass(frozen=True)
class LocalRepositoryConfig:
    driver: str
    parameters: Parameters = frozendict()


@pydantic_dataclass(frozen=True)
class RemoteRepositoryConfig:
    url: AnyUrl
    cache_path: Annotated[Path, WithVariables]


@pydantic_dataclass(frozen=True)
class RepositoryDriverConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class RequirementTranslatorConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class InstallerConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class Config:
    repository_drivers: Mapping[str, RepositoryDriverConfig]
    requirement_translators: Mapping[str, RequirementTranslatorConfig]
    installers: Mapping[str, InstallerConfig]
    repositories: list[RemoteRepositoryConfig | LocalRepositoryConfig]


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any


ResolutionModel = Mapping[Package, str]
