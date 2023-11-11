from collections.abc import Mapping, Set
from typing import Any

from PPpackage_utils.parse import FrozenAny
from pydantic import BaseModel


class Input(BaseModel):
    requirements: Mapping[str, Set[FrozenAny]]
    options: Mapping[str, Mapping[str, Any] | None]
    generators: Set[str]
