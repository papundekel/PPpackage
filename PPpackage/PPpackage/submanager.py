from collections.abc import Iterable, Mapping, MutableSequence, Set
from pathlib import Path
from typing import Any, ClassVar, Final, Protocol, Self

from httpx import AsyncClient as HTTPClient
from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    Product,
    ResolutionGraph,
)
from PPpackage_utils.tar import create_empty as create_empty_tar
from pydantic import HttpUrl

from .install import install
from .schemes import SubmanagerLocalConfig
from .utils import NodeData


class Submanager(Protocol):
    local: ClassVar[bool]
    name: Final[str]

    def __init__(self, name: str):
        self.name = name

    async def update_database(self) -> None:
        ...

    async def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
        resolution_graphs: Mapping[str, MutableSequence[ResolutionGraph]],
    ) -> None:
        ...

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
    ) -> None:
        ...

    async def install(self, id: int, installation_path: Path, product: Product) -> None:
        ...

    async def install_init(self, installation_path: Path) -> int:
        ...

    async def install_send(
        self, source_id: int, destination: Self, destination_id: int | None
    ) -> int:
        ...

    async def install_delete(self, id: int) -> None:
        ...

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None:
        ...


class RemoteSubmanager(Submanager):
    local = False

    def __init__(self, name: str, client: HTTPClient):
        super().__init__(name)

        self.client = client

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

    async def install(self, id: int, installation_path: Path, product: Product) -> None:
        pass

    async def install_init(self, installation_path: Path) -> int:
        return 0

    async def install_send(
        self, source_id: int, destination: Self, destination_id: int | None
    ) -> int:
        return 0

    async def install_delete(self, id: int) -> None:
        pass

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
    ) -> memoryview:
        return memoryview(b"")


# async def build_install(
#     submanagers: Mapping[str, Submanager],
#     install_order: Iterable[tuple[ManagerAndName, NodeData]],
#     dependencies: Iterable[tuple[ManagerAndName, NodeData]],
# ):
#     dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

#     dependency_install_order = [
#         (node, data) for node, data in install_order if node in dependency_set
#     ]

#     return await install(submanagers, dependency_install_order)


def Submanagers(
    config: Mapping[str, HttpUrl | SubmanagerLocalConfig]
) -> Mapping[str, Submanager]:
    return {}
