from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

ParametersType = TypeVar("ParametersType", bound=BaseModel)


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[ParametersType]):
    Parameters: type[ParametersType]
    install: Callable[
        [ParametersType, Path, Path],
        Awaitable[None],
    ]
