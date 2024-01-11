from collections.abc import AsyncIterable, Iterable, Mapping, MutableSequence, Set
from pathlib import Path
from typing import Any, Final, Protocol, Self

from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    Product,
    ResolutionGraph,
)

from PPpackage.generate import generate

from .install import install
from .utils import NodeData


class Submanager(Protocol):
    name: Final[str]

    def __init__(self, name: str):
        self.name = name

    async def close(self) -> None:
        pass

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

    async def install(self, id: str, installation_path: Path, product: Product) -> None:
        ...

    async def install_init(self, installation_path: Path) -> str:
        ...

    async def install_send(
        self, source_id: str, destination: Self, destination_id: str | None
    ) -> str:
        ...

    async def install_receive(
        self, destination_id: str | None, installation_path: Path
    ) -> str:
        ...

    async def install_delete(self, id: str) -> None:
        ...

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None:
        ...


async def fetch_install(
    submanagers: Mapping[str, Submanager],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
):
    dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

    dependency_install_order = [
        (node, data) for node, data in install_order if node in dependency_set
    ]

    return await install(submanagers, dependency_install_order, destination_path)


async def fetch_generate(
    submanagers: Mapping[str, Submanager],
    generators: AsyncIterable[str],
    nodes: Iterable[tuple[ManagerAndName, NodeData]],
    meta_options: Mapping[str, Options],
    destination_path: Path,
):
    generators_list = [generator async for generator in generators]

    await generate(submanagers, generators_list, nodes, meta_options, destination_path)
