from collections.abc import AsyncIterable, MutableSequence
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    DiscoveryPackageInfo,
    PackageDetail,
    Requirement,
)


class Repository(Protocol):
    translated_options: Any

    def get_identifier(self) -> str: ...

    def get_url(self) -> str: ...

    def discover_packages(self) -> AsyncIterable[DiscoveryPackageInfo]: ...

    async def translate_options(self, options: Any) -> Any: ...

    def get_formula(self) -> AsyncIterable[Requirement]: ...

    async def translate_options_and_get_formula(
        self, options: Any, formula: MutableSequence[Requirement]
    ) -> None:
        self.translated_options = await self.translate_options(options)
        async for requirement in self.get_formula():
            formula.append(requirement)

    async def get_package_detail(self, package: str) -> PackageDetail: ...
