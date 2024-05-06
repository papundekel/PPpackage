from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    BuildContextInfo,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)
from pydantic import AnyUrl

from PPpackage.utils.utils import Result


class RepositoryInterface(Protocol):
    def get_identifier(self) -> str: ...

    def get_url(self) -> AnyUrl | None: ...

    async def get_epoch(self) -> str: ...

    def fetch_translator_data(
        self, epoch_result: Result[str]
    ) -> AsyncIterable[TranslatorInfo]: ...

    async def translate_options(self, options: Any) -> tuple[str, Any]: ...

    def get_formula(
        self, translated_options: Any, epoch_result: Result[str]
    ) -> AsyncIterable[Requirement]: ...

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None: ...

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail: ...

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_context_info: BuildContextInfo,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo: ...
