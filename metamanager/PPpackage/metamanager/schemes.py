from collections.abc import Awaitable, Mapping
from pathlib import Path
from typing import Annotated, Any, TypedDict

from frozendict import frozendict
from PPpackage.repository_driver.interface.schemes import (
    BaseModuleConfig,
    PackageDetail,
    Parameters,
    ProductInfo,
    Requirement,
)
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass

from metamanager.PPpackage.metamanager.repository import Repository
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
    product_cache_path: Annotated[Path, WithVariables]
    repository_drivers: Mapping[str, RepositoryDriverConfig] = frozendict()


class NodeData(TypedDict):
    repository: Repository
    detail: Awaitable[PackageDetail]
    product: Awaitable[tuple[Path, str]]
    product_info: Awaitable[ProductInfo]
