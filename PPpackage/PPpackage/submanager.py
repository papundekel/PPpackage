from collections.abc import AsyncIterable, Iterable, Set
from pathlib import Path
from typing import Any, AsyncContextManager, Final, Protocol, Self

from PPpackage_submanager.schemes import (
    Dependency,
    Options,
    Package,
    Product,
    ProductIDAndInfo,
    ResolutionGraph,
)


class Submanager(Protocol):
    name: Final[str]

    def __init__(self, name: str):
        self.name = name

    async def update_database(self) -> None: ...

    def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
    ) -> AsyncIterable[ResolutionGraph]: ...

    def fetch(
        self,
        options: Options,
        package: Package,
        dependencies: Iterable[Dependency],
        installation_path: Path | None,
        generators_path: Path | None,
    ) -> AsyncContextManager[ProductIDAndInfo | AsyncIterable[str]]: ...

    async def install(
        self, id: str, installation_path: Path, product: Product
    ) -> None: ...

    async def install_init(self, installation_path: Path) -> str: ...

    async def install_send(
        self,
        source_id: str,
        destination: Self,
        destination_id: str | None,
        installation_path: Path,
    ) -> str: ...

    async def install_receive(
        self,
        destination_id: str | None,
        installation: memoryview | None,
        installation_path: Path,
    ) -> str: ...

    async def install_download(self, id: str, installation_path: Path) -> None: ...

    async def install_delete(self, id: str) -> None: ...

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None: ...
