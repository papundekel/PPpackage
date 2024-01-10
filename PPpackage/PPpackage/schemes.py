from collections.abc import Mapping, Set
from pathlib import Path
from typing import Any

from PPpackage_submanager.schemes import FrozenAny, Options
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Input:
    requirements: Mapping[str, Set[FrozenAny]]
    options: Mapping[str, Options] | None = None
    generators: Set[str] | None = None


@dataclass(frozen=True)
class SubmanagerLocalConfig:
    path: Path
    settings: Any


@dataclass(frozen=True)
class Config:
    submanagers: Mapping[str, HttpUrl | SubmanagerLocalConfig]
