from collections.abc import Iterable, Mapping, MutableSequence, Set
from pathlib import Path
from typing import Any, Self

from httpx import AsyncClient as HTTPClient
from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    Product,
    ResolutionGraph,
)
from pydantic import HttpUrl

from .submanager import Submanager
from .utils import NodeData


class RemoteSubmanager(Submanager):
    def __init__(self, name: str, client: HTTPClient, url: HttpUrl):
        super().__init__(name)

        self.client = client
        self.url = url

    async def close(self) -> None:
        pass

    async def update_database(self) -> None:
        pass

    async def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
        resolution_graphs: Mapping[str, MutableSequence[ResolutionGraph]],
    ) -> None:
        pass

    async def fetch(
        self,
        options: Options,
        package: Package,
        dependencies: Iterable[Dependency],
        nodes: Mapping[ManagerAndName, NodeData],
        packages_to_dependencies: Mapping[
            ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
        ],
        install_order: Iterable[tuple[ManagerAndName, NodeData]],
    ):
        pass

    async def install(self, id: str, installation_path: Path, product: Product) -> None:
        pass

    async def install_init(self, installation_path: Path) -> str:
        return ""

    async def install_send(
        self, source_id: str, destination: Self, destination_id: str | None
    ) -> str:
        return ""

    async def install_receive(
        self, destination_id: str | None, installation_path: Path
    ) -> str:
        return ""

    async def install_delete(self, id: str) -> None:
        pass

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None:
        pass
