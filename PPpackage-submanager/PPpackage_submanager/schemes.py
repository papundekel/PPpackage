from collections.abc import Iterable, Mapping
from typing import Annotated, Any

from frozendict import frozendict
from pydantic import BeforeValidator
from pydantic.dataclasses import dataclass


def frozen_validator(value: Any) -> Any:
    if type(value) is dict:
        return frozendict(value)

    return value


FrozenAny = Annotated[Any, BeforeValidator(frozen_validator)]


Options = Mapping[str, Any] | None


@dataclass(frozen=True)
class Product:
    name: str
    version: str
    product_id: str


@dataclass(frozen=True)
class PackageIDAndInfo:
    product_id: str
    product_info: Any


@dataclass(frozen=True)
class ManagerAndName:
    manager: str
    name: str


@dataclass(frozen=True)
class Dependency(ManagerAndName):
    product_info: Any | None


@dataclass(frozen=True)
class Package:
    name: str
    version: str


@dataclass(frozen=True)
class ManagerRequirement:
    manager: str
    requirement: Any


@dataclass(frozen=True)
class ResolutionGraphNode:
    name: str
    version: str
    dependencies: Iterable[str]
    requirements: Iterable[ManagerRequirement]


@dataclass(frozen=True)
class ResolutionGraph:
    roots: Iterable[Iterable[str]]
    graph: Iterable[ResolutionGraphNode]
