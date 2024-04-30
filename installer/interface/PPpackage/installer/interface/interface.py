from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


@dataclass(frozen=True, kw_only=True)
class Interface[ParametersType: BaseModel]:
    Parameters: type[ParametersType]
    install: Callable[
        [ParametersType, Path, Path],
        Awaitable[None],
    ]
