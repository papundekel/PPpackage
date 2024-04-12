from collections.abc import AsyncIterable, MutableSequence
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    DetailPackageInfo,
    DiscoveryPackageInfo,
    Requirement,
)


class Repository(Protocol):
    def get_identifier(self) -> str: ...

    def discover_packages(self) -> AsyncIterable[DiscoveryPackageInfo]: ...

    async def translate_options(self, options: Any) -> Any: ...

    def get_formula(self, translated_options: Any) -> AsyncIterable[Requirement]: ...

    async def translate_options_and_get_formula(
        self, options: Any, formula: MutableSequence[Requirement]
    ) -> None:
        translated_options = await self.translate_options(options)
        async for requirement in self.get_formula(translated_options):
            formula.append(requirement)

    async def get_package_detail(self, package: str) -> DetailPackageInfo: ...
