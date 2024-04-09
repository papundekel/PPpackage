from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Generic, TypeVar
from typing import cast as type_cast

from PPpackage_repository_driver.schemes import (
    ResolutionLiteral,
    VariableToPackageVersionMapping,
)
from pydantic import BaseModel

ParametersType = TypeVar("ParametersType", bound=BaseModel)

TranslateOptionsCallbackType = Callable[[ParametersType, Any, Any], Awaitable[Any]]
FetchPackagesCallbackType = Callable[
    [
        ParametersType,
        Any,
        Any,
    ],
    AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping],
]


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[ParametersType]):
    translate_options: TranslateOptionsCallbackType[ParametersType]
    fetch_packages: FetchPackagesCallbackType[ParametersType]


def load_interface_module(package_name: str) -> Interface:
    return type_cast(Interface, import_module(f"{package_name}.interface").interface)
