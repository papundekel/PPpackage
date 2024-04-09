from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Generic, TypeVar
from typing import cast as type_cast

from pydantic import BaseModel

from .schemes import ResolutionLiteral, VariableToPackageVersionMapping

DriverParametersType = TypeVar("DriverParametersType", bound=BaseModel)
RepositoryParametersType = TypeVar("RepositoryParametersType", bound=BaseModel)

TranslateOptionsCallbackType = Callable[
    [DriverParametersType, RepositoryParametersType, Any], Awaitable[Any]
]
FetchPackagesCallbackType = Callable[
    [
        DriverParametersType,
        RepositoryParametersType,
        Any,
    ],
    AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping],
]


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[DriverParametersType, RepositoryParametersType]):
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    translate_options: TranslateOptionsCallbackType[
        DriverParametersType, RepositoryParametersType
    ]
    fetch_packages: FetchPackagesCallbackType[
        DriverParametersType, RepositoryParametersType
    ]


def load_interface_module(package_name: str) -> Interface:
    return type_cast(Interface, import_module(f"{package_name}.interface").interface)
