from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel
from pysat.formula import Formula

ParametersType = TypeVar("ParametersType", bound=BaseModel)


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[ParametersType]):
    Parameters: type[ParametersType]
    install: Callable[
        [ParametersType, Mapping[str, Iterable[str]]],
        Awaitable[None],
    ]
