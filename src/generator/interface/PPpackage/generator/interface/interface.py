from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


@dataclass(frozen=True, kw_only=True)
class Interface[ParametersType: BaseModel]:
    Parameters: type[ParametersType]
    generate: Callable[
        [ParametersType, str, Iterable[tuple[str, Path]], Path],
        Awaitable[None],
    ]
