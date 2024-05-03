from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

from annotated_types import Len
from frozendict import frozendict
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass(frozen=True)
class SimpleRequirement:
    translator: str
    value: Any


@pydantic_dataclass(frozen=True)
class NegatedRequirement:
    negated: "Requirement"


@pydantic_dataclass(frozen=True)
class ANDRequirement:
    and_: list["Requirement"]


@pydantic_dataclass(frozen=True)
class ORRequirement:
    or_: list["Requirement"]


@pydantic_dataclass(frozen=True)
class XORRequirement:
    xor: Annotated[list["Requirement"], Len(1)]


@pydantic_dataclass(frozen=True)
class EquivalenceRequirement:
    equivalent: Annotated[list["Requirement"], Len(1)]


@pydantic_dataclass(frozen=True)
class ImplicationRequirement:
    if_: "Requirement"
    implies: "Requirement"


Requirement = (
    SimpleRequirement
    | NegatedRequirement
    | ANDRequirement
    | ORRequirement
    | XORRequirement
    | ImplicationRequirement
    | EquivalenceRequirement
)


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
    requirement: Requirement
    options: Any
    on_top: bool


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
type ProductInfos = Mapping[str, Mapping[str, Any]]
