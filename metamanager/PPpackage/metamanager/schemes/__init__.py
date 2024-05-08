from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from frozendict import frozendict
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.container_utils.schemes import ContainerizerConfig
from PPpackage.repository_driver.interface.schemes import (
    BaseModuleConfig,
    Parameters,
    Requirement,
)
from PPpackage.utils.validation import WithVariables


@pydantic_dataclass(frozen=True)
class Input:
    requirements: list[Requirement]
    options: Any = None
    build_options: Any = None
    locks: Mapping[str, Mapping[str, str]] = frozendict()
    generators: frozenset[str] | None = None


@pydantic_dataclass(frozen=True)
class RepositoryConfig:
    formula_cache_path: Annotated[Path, WithVariables]
    translator_data_cache_path: Annotated[Path, WithVariables]


@pydantic_dataclass(frozen=True)
class LocalRepositoryConfig(RepositoryConfig):
    driver: str
    parameters: Parameters = frozendict()


@pydantic_dataclass(frozen=True)
class RemoteRepositoryConfig(RepositoryConfig):
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
    containerizer: ContainerizerConfig
    containerizer_workdir: Annotated[Path, WithVariables]
    repository_drivers: Mapping[str, RepositoryDriverConfig] = frozendict()


@dataclass(frozen=True)
class Literal:
    symbol: str
    polarity: bool
