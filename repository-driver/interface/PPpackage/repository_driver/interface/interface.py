from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Generic, TypeVar
from typing import cast as type_cast

from pydantic import BaseModel

from .schemes import FetchPackageInfo, Requirement

DriverParametersType = TypeVar("DriverParametersType", bound=BaseModel)
RepositoryParametersType = TypeVar("RepositoryParametersType", bound=BaseModel)
TranslatedOptionsType = TypeVar("TranslatedOptionsType")

FetchPackagesCallbackType = Callable[
    [
        DriverParametersType,
        RepositoryParametersType,
    ],
    AsyncIterable[FetchPackageInfo],
]
TranslateOptionsCallbackType = Callable[
    [DriverParametersType, RepositoryParametersType, Any],
    Awaitable[TranslatedOptionsType],
]
FetchFormulaCallbackType = Callable[
    [
        DriverParametersType,
        RepositoryParametersType,
        TranslatedOptionsType,
    ],
    AsyncIterable[Requirement],
]


@dataclass(frozen=True, kw_only=True)
class Interface(
    Generic[DriverParametersType, RepositoryParametersType, TranslatedOptionsType]
):
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    TranslatedOptions: type[TranslatedOptionsType]
    fetch_packages: FetchPackagesCallbackType[
        DriverParametersType, RepositoryParametersType
    ]
    translate_options: TranslateOptionsCallbackType[
        DriverParametersType, RepositoryParametersType, TranslatedOptionsType
    ]
    fetch_formula: FetchFormulaCallbackType[
        DriverParametersType, RepositoryParametersType, TranslatedOptionsType
    ]
