from collections.abc import Mapping, Set
from pathlib import Path
from typing import Optional

from PPpackage_utils.parse import FrozenAny, Options
from pydantic import BaseModel


class Input(BaseModel):
    options: Mapping[str, Options] | None = None
    generators: Set[str] | None = None
    requirements: Mapping[str, Set[FrozenAny]]


class Config(BaseModel):
    submanager_socket_paths: Mapping[str, Path]
