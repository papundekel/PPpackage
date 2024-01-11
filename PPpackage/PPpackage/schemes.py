from collections.abc import Mapping, Set
from typing import Any, TypedDict

from PPpackage_submanager.schemes import FrozenAny, Options
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Input:
    requirements: Mapping[str, Set[FrozenAny]]
    options: Mapping[str, Options] | None = None
    generators: Set[str] | None = None


@dataclass(frozen=True)
class LocalSubmanagerConfig:
    package: str
    settings: Any


@dataclass(frozen=True)
class RemoteSubmanagerConfig:
    url: HttpUrl
    token: str


@dataclass(frozen=True)
class Config:
    submanagers: Mapping[str, RemoteSubmanagerConfig | LocalSubmanagerConfig]


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any
