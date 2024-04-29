from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel
from pysat.formula import Formula


@dataclass(frozen=True, kw_only=True)
class Interface[ParametersType: BaseModel, RequirementType]:
    Parameters: type[ParametersType]
    Requirement: type[RequirementType]
    translate_requirement: Callable[
        [ParametersType, Mapping[str, Iterable[dict[str, str]]], RequirementType],
        Awaitable[Formula],
    ]
