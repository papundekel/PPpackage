from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, AsyncContextManager

from pydantic import BaseModel

from PPpackage.utils.utils import Result

from .schemes import (
    BuildContextDetail,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)


@dataclass(frozen=True, kw_only=True)
class Interface[
    DriverParametersType: BaseModel,
    RepositoryParametersType: BaseModel,
    TranslatedOptionsType,
    StateType,
]:
    DriverParameters: type[DriverParametersType]
    RepositoryParameters: type[RepositoryParametersType]
    TranslatedOptions: type[TranslatedOptionsType]

    lifespan: Callable[
        [DriverParametersType, RepositoryParametersType], AsyncContextManager[StateType]
    ]

    update: Callable[
        [StateType, DriverParametersType, RepositoryParametersType], Awaitable[None]
    ]

    get_epoch: Callable[
        [StateType, DriverParametersType, RepositoryParametersType], Awaitable[str]
    ]

    fetch_translator_data: Callable[
        [StateType, DriverParametersType, RepositoryParametersType, Result[str]],
        AsyncIterable[TranslatorInfo],
    ]

    translate_options: Callable[
        [StateType, DriverParametersType, RepositoryParametersType, Any],
        Awaitable[tuple[str, TranslatedOptionsType]],
    ]

    get_formula: Callable[
        [
            StateType,
            DriverParametersType,
            RepositoryParametersType,
            TranslatedOptionsType,
            Result[str],
        ],
        AsyncIterable[Requirement],
    ]

    get_package_detail: Callable[
        [
            StateType,
            DriverParametersType,
            RepositoryParametersType,
            TranslatedOptionsType,
            str,
        ],
        Awaitable[PackageDetail | None],
    ]

    get_build_context: Callable[
        [
            StateType,
            DriverParametersType,
            RepositoryParametersType,
            TranslatedOptionsType,
            str,
            ProductInfos,
        ],
        Awaitable[BuildContextDetail],
    ]

    compute_product_info: Callable[
        [
            StateType,
            DriverParametersType,
            RepositoryParametersType,
            TranslatedOptionsType,
            str,
            ProductInfos,
            ProductInfos,
        ],
        Awaitable[ProductInfo],
    ]
