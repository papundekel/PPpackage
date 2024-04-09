from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Generic, TypeVar
from typing import cast as type_cast

from pydantic import BaseModel

from .schemes import ResolutionLiteral, VariableToPackageVersionMapping

DriverParametersType = TypeVar("DriverParametersType", bound=BaseModel)
RepositoryParametersType = TypeVar("RepositoryParametersType", bound=BaseModel)
TranslatedOptionsType = TypeVar("TranslatedOptionsType")

TranslateOptionsCallbackType = Callable[
    [DriverParametersType, RepositoryParametersType, Any],
    Awaitable[TranslatedOptionsType],
]
FetchPackagesCallbackType = Callable[
    [
        DriverParametersType,
        RepositoryParametersType,
        TranslatedOptionsType,
    ],
    AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping],
]


@dataclass(frozen=True, kw_only=True)
class Interface(
    Generic[DriverParametersType, RepositoryParametersType, TranslatedOptionsType]
):
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    TranslatedOptions: type[TranslatedOptionsType]
    translate_options: TranslateOptionsCallbackType[
        DriverParametersType, RepositoryParametersType, TranslatedOptionsType
    ]
    fetch_packages: FetchPackagesCallbackType[
        DriverParametersType, RepositoryParametersType, TranslatedOptionsType
    ]


def load_interface_module(package_name: str) -> Interface:
    return type_cast(Interface, import_module(f"{package_name}.interface").interface)
