from collections.abc import AsyncIterable, Callable, Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True, kw_only=True)
class Interface[ParametersType: BaseModel, RequirementType]:
    Parameters: type[ParametersType]
    Requirement: type[RequirementType]
    translate_requirement: Callable[
        [ParametersType, Mapping[str, Iterable[dict[str, str]]], RequirementType],
        Iterable[str],
    ]
