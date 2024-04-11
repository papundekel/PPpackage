from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Annotated, Any, TypedDict

from frozendict import frozendict
from PPpackage.repository_driver.interface.schemes import (
    BaseModuleConfig,
    Parameters,
    Requirement,
)
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.validation import WithVariables


@pydantic_dataclass(frozen=True)
class Input:
    requirements: Requirement
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
    requirement_translators: Mapping[str, RequirementTranslatorConfig]
    installers: Mapping[str, InstallerConfig]
    repositories: list[RemoteRepositoryConfig | LocalRepositoryConfig]
    repository_drivers: Mapping[str, RepositoryDriverConfig] = frozendict()


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any
