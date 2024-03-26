from collections.abc import AsyncIterable, Iterable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any

from frozendict import frozendict
from pydantic import BaseModel, BeforeValidator
from pydantic.dataclasses import dataclass as pydantic_dataclass


def frozen_validator(value: Any) -> Any:
    if type(value) is dict:
        return frozendict(value)

    return value


FrozenAny = Annotated[Any, BeforeValidator(frozen_validator)]


Options = Mapping[str, Any] | None


@pydantic_dataclass(frozen=True)
class Product:
    name: str
    version: str
    product_id: str


@pydantic_dataclass(frozen=True)
class ProductIDAndInfo:
    product_id: str
    product_info: Any


@pydantic_dataclass(frozen=True)
class ManagerAndName:
    manager: str
    name: str


@pydantic_dataclass(frozen=True)
class Dependency(ManagerAndName):
    product_info: Any | None


@pydantic_dataclass(frozen=True)
class Package:
    name: str
    version: str


@pydantic_dataclass(frozen=True)
class ManagerRequirement:
    manager: str
    requirement: Any


@pydantic_dataclass(frozen=True)
class ResolutionGraphNode:
    name: str
    version: str
    dependencies: Iterable[str]
    requirements: Iterable[ManagerRequirement]


@pydantic_dataclass(frozen=True)
class ResolutionGraph:
    roots: Iterable[Iterable[str]]
    graph: Iterable[ResolutionGraphNode]


class UserCreated(BaseModel):
    token: str


@dataclass(frozen=True)
class FetchRequest:
    requirements: AsyncIterable[tuple[str, Any]]
    generators: AsyncIterable[str]


@pydantic_dataclass(frozen=True)
class Lock:
    lock: str
    version: str
