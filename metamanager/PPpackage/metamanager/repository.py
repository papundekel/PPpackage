from collections.abc import AsyncIterable, MutableSequence
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo, Requirement


class Repository(Protocol):
    def fetch_packages(self) -> AsyncIterable[FetchPackageInfo]: ...

    async def translate_options(self, options: Any) -> Any: ...

    def fetch_formula(self, translated_options: Any) -> AsyncIterable[Requirement]: ...

    async def translate_options_and_fetch_formula(
        self, options: Any, formula: MutableSequence[Requirement]
    ) -> None:
        translated_options = await self.translate_options(options)
        async for requirement in self.fetch_formula(translated_options):
            formula.append(requirement)
