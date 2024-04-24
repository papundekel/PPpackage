from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    PackageDetail,
    ProductInfo,
    Requirement,
    TranslatorInfo,
)
from pydantic import AnyUrl


class Repository(Protocol):
    translated_options: Any

    def get_identifier(self) -> str: ...

    def get_url(self) -> AnyUrl | None: ...

    def fetch_translator_data(self) -> AsyncIterable[TranslatorInfo]: ...

    async def _translate_options(self, options: Any) -> Any: ...

    def get_formula(self) -> AsyncIterable[Requirement]: ...

    async def translate_options_and_get_formula(
        self, options: Any
    ) -> AsyncIterable[Requirement]:
        self.translated_options = await self._translate_options(options)
        async for requirement in self.get_formula():
            yield requirement

    async def get_package_detail(self, package: str) -> PackageDetail | None: ...

    async def compute_product_info(
        self, package: str, dependency_product_infos: DependencyProductInfos
    ) -> ProductInfo: ...
