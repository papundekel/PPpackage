from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from .schemes import PackageDetail, ProductInfo, Requirement, TranslatorInfo


@dataclass(frozen=True, kw_only=True)
class Interface[
    DriverParametersType: BaseModel,
    RepositoryParametersType: BaseModel,
    TranslatedOptionsType,
]:
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    TranslatedOptions: type[TranslatedOptionsType]

    update: Callable[[DriverParametersType, RepositoryParametersType], Awaitable[None]]

    get_epoch: Callable[
        [DriverParametersType, RepositoryParametersType], Awaitable[str]
    ]

    fetch_translator_data: Callable[
        [DriverParametersType, RepositoryParametersType, str],
        AsyncIterable[TranslatorInfo],
    ]

    translate_options: Callable[
        [DriverParametersType, RepositoryParametersType, str, Any],
        Awaitable[TranslatedOptionsType],
    ]

    get_formula: Callable[
        [DriverParametersType, RepositoryParametersType, str, TranslatedOptionsType],
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
