from collections.abc import Callable, Iterable
from dataclasses import dataclass

from pydantic import BaseModel

from .schemes import Data, Literal


@dataclass(frozen=True, kw_only=True)
class Interface[ParametersType: BaseModel, RequirementType]:
    Parameters: type[ParametersType]
    Requirement: type[RequirementType]
    get_assumptions: Callable[[ParametersType, Data], Iterable[Literal]]
    translate_requirement: Callable[
        [ParametersType, Data, RequirementType],
        Iterable[str],
    ]
