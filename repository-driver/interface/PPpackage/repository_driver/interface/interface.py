from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .schemes import PackageDetail, ProductInfo, Requirement, TranslatorInfo

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

    fetch_translator_data: Callable[
        [DriverParametersType, RepositoryParametersType],
        AsyncIterable[TranslatorInfo],
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
        [DriverParametersType, RepositoryParametersType, TranslatedOptionsType, str],
        Awaitable[PackageDetail | None],
    ]

    compute_product_info: Callable[
        [
            DriverParametersType,
            RepositoryParametersType,
            TranslatedOptionsType,
            str,
            Mapping[str, Mapping[str, Any]],
        ],
        Awaitable[ProductInfo],
    ]
