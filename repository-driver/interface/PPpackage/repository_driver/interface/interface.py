from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .schemes import DiscoveryPackageInfo, PackageDetail, Requirement

DriverParametersType = TypeVar("DriverParametersType", bound=BaseModel)
RepositoryParametersType = TypeVar("RepositoryParametersType", bound=BaseModel)
TranslatedOptionsType = TypeVar("TranslatedOptionsType")


@dataclass(frozen=True, kw_only=True)
class Interface(
    Generic[DriverParametersType, RepositoryParametersType, TranslatedOptionsType]
):
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    TranslatedOptions: type[TranslatedOptionsType]

    get_epoch: Callable[
        [DriverParametersType, RepositoryParametersType], Awaitable[str]
    ]

    discover_packages: Callable[
        [DriverParametersType, RepositoryParametersType],
        AsyncIterable[DiscoveryPackageInfo],
    ]

    translate_options: Callable[
        [DriverParametersType, RepositoryParametersType, Any],
        Awaitable[TranslatedOptionsType],
    ]

    get_formula: Callable[
        [DriverParametersType, RepositoryParametersType, TranslatedOptionsType],
        AsyncIterable[Requirement],
    ]

    get_package_detail: Callable[
        [DriverParametersType, RepositoryParametersType, str],
        Awaitable[PackageDetail],
    ]
