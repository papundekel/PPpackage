from collections.abc import Iterable, Mapping, Set
from pathlib import Path
from typing import Any, Literal, TypedDict

from frozendict import frozendict
from PPpackage_repository_driver.schemes import BaseModuleConfig, Package, Parameters
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass(frozen=True)
class SimpleRequirementInput:
    translator: str
    value: Any


@pydantic_dataclass(frozen=True)
class OperatorRequirementInput:
    operation: Literal["and"] | Literal["or"]
    operands: Iterable["RequirementInput"]


RequirementInput = SimpleRequirementInput | OperatorRequirementInput


@pydantic_dataclass(frozen=True)
class Input:
    requirements: RequirementInput
    options: Any
    locks: Mapping[str, Mapping[str, str]] = frozendict()
    generators: Set[str] | None = None


@pydantic_dataclass(frozen=True)
class LocalRepositoryConfig:
    driver: str
    parameters: Parameters = {}


@pydantic_dataclass(frozen=True)
class RemoteRepositoryConfig:
    url: AnyUrl
    cache_path: Path


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
    repositories: Iterable[RemoteRepositoryConfig | LocalRepositoryConfig]


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any


ResolutionModel = Mapping[Package, str]
