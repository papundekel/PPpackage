from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage_repository_driver.schemes import (
    ResolutionLiteral,
    VariableToPackageVersionMapping,
)


class Repository(Protocol):
    async def translate_options(self, options: Any) -> Any: ...

    def fetch_packages(
        self,
        translated_options: Any,
    ) -> AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping]: ...
