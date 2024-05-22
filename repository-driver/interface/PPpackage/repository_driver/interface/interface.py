from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncContextManager

from PPpackage.utils.async_ import Result
from pydantic import BaseModel

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
        [DriverParametersType, RepositoryParametersType, Path],
        AsyncContextManager[StateType],
    ]

    update: Callable[[StateType], Awaitable[None]]

    get_epoch: Callable[[StateType], Awaitable[str]]

    fetch_translator_data: Callable[
        [StateType, Result[str]], AsyncIterable[TranslatorInfo]
    ]

    translate_options: Callable[
        [StateType, Any], Awaitable[tuple[str, TranslatedOptionsType]]
    ]

    get_formula: Callable[
        [StateType, TranslatedOptionsType, Result[str]],
        AsyncIterable[list[Requirement]],
    ]

    get_package_detail: Callable[
        [StateType, TranslatedOptionsType, str], Awaitable[PackageDetail | None]
    ]

    get_build_context: Callable[
        [StateType, TranslatedOptionsType, str, ProductInfos],
        Awaitable[BuildContextDetail],
    ]

    compute_product_info: Callable[
        [StateType, TranslatedOptionsType, str, ProductInfos, ProductInfos],
        Awaitable[ProductInfo],
    ]
