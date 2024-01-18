from collections.abc import Mapping, Set
from pathlib import Path
from typing import Any, TypedDict

from PPpackage_submanager.schemes import FrozenAny, Options
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Input:
    requirements: Mapping[str, Set[FrozenAny]]
    options: Mapping[str, Options] | None = None
    generators: Set[str] | None = None


@dataclass(frozen=True)
class LocalSubmanagerConfig:
    package: str
    settings: Mapping


@dataclass(frozen=True)
class RemoteSubmanagerConfig:
    url: AnyUrl
    token_path: Path


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any
