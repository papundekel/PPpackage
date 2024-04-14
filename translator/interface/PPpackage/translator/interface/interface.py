from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel
from pysat.formula import Formula

ParametersType = TypeVar("ParametersType", bound=BaseModel)
RequirementType = TypeVar("RequirementType")


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[ParametersType, RequirementType]):
    Parameters: type[ParametersType]
    Requirement: type[RequirementType]
    translate_requirement: Callable[
        [ParametersType, Mapping[str, Iterable[str]], RequirementType],
        Awaitable[Formula],
    ]
