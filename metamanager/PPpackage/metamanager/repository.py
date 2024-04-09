from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import PackageVersion


class Repository(Protocol):
    async def translate_options(self, options: Any) -> Any: ...

    def fetch_packages(
        self,
        translated_options: Any,
    ) -> AsyncIterable[PackageVersion]: ...
