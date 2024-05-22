from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

from frozendict import frozendict
from PPpackage.repository_driver.interface.schemes import (
    BaseModuleConfig,
    Parameters,
    Requirement,
)
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.container.schemes import ContainerizerConfig
from PPpackage.utils.json.validator import WithVariables


@pydantic_dataclass(frozen=True)
class Input:
    requirements: list[Requirement]
    options: Any = None
    build_options: Any = None
    locks: Mapping[str, Mapping[str, str]] = frozendict()
    generators: frozenset[str] = frozenset()


class RepositoryConfig(BaseModel):
    driver: str
    parameters: Parameters = frozendict()
    formula_cache_path: Annotated[Path, WithVariables] | None = None
    translator_data_cache_path: Annotated[Path, WithVariables] | None = None


@pydantic_dataclass(frozen=True)
class RepositoryDriverConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class TranslatorConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class InstallerConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class GeneratorConfig(BaseModuleConfig):
    pass


@pydantic_dataclass(frozen=True)
class Config:
    translators: Mapping[str, TranslatorConfig]
    installers: Mapping[str, InstallerConfig]
    repositories: list[RepositoryConfig]
    containerizer: ContainerizerConfig
    containerizer_workdir: Annotated[Path, WithVariables] = Path("/tmp")
    data_path: Annotated[Path, WithVariables] = Path.home() / ".PPpackage/"
    product_cache_path: Annotated[Path, WithVariables] | None = None
    repository_drivers: Mapping[str, RepositoryDriverConfig] = frozendict()
    generators: Mapping[str, GeneratorConfig] = frozendict()
