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
    and_: Annotated[list["Requirement"], Len(1)]


@pydantic_dataclass(frozen=True)
class ORRequirement:
    or_: Annotated[list["Requirement"], Len(1)]


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
class DiscoveryPackageInfo:
    package: str
    translator_groups: frozenset[str]


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
class TagProductDetail:
    tag: str


@pydantic_dataclass(frozen=True)
class ContainerfileProductDetail:
    containerfile: str


@pydantic_dataclass(frozen=True)
class MetaProductDetail:
    meta: Requirement


@pydantic_dataclass(frozen=True)
class MetaOnTopProductDetail:
    meta_on_top: Requirement


@pydantic_dataclass(frozen=True)
class ArchiveProductDetail:
    archive: HttpUrl | Path
    installer: str


@pydantic_dataclass(frozen=True)
class DetailPackageInfo:
    interfaces: frozenset[str]
    dependencies: frozenset[str]
    product: (
        TagProductDetail
        | ContainerfileProductDetail
        | MetaProductDetail
        | MetaOnTopProductDetail
        | ArchiveProductDetail
    )
