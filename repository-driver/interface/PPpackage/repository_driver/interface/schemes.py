from collections.abc import Mapping
from pathlib import Path
from typing import Any

from frozendict import frozendict
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass(frozen=True)
class Requirement:
    translator: str
    value: Any
    polarity: bool = True


@pydantic_dataclass(frozen=True)
class TranslatorInfo:
    group: str
    symbol: dict[str, str]


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


@pydantic_dataclass(frozen=True)
class TagBuildContextDetail:
    tag: str


@pydantic_dataclass(frozen=True)
class ContainerfileBuildContextDetail:
    containerfile: bytes


@pydantic_dataclass(frozen=True)
class MetaBuildContextDetail:
    requirements: list[Requirement]
    on_top: bool
    command: list[str]


@pydantic_dataclass(frozen=True)
class ArchiveBuildContextDetail:
    archive: HttpUrl | Path
    installer: str


type BuildContextDetail = (
    TagBuildContextDetail
    | ContainerfileBuildContextDetail
    | MetaBuildContextDetail
    | ArchiveBuildContextDetail
)


@pydantic_dataclass(frozen=True)
class PackageDetail:
    interfaces: frozenset[str]
    dependencies: frozenset[str]


type ProductInfo = Mapping[str, Any]
type BuildContextInfo = Mapping[str, Any]
type ProductInfos = Mapping[str, Mapping[str, Any]]
