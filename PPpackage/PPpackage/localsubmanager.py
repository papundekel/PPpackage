from asyncio import TaskGroup
from collections.abc import AsyncGenerator, Iterable, Mapping, MutableSequence, Set
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any
from typing import cast as type_cast

from PPpackage_submanager.interface import Interface
from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
)
from PPpackage_utils.utils import TemporaryDirectory, make_async_iterable

from .schemes import SubmanagerLocalConfig
from .submanager import Submanager, fetch_generate, fetch_install
from .utils import NodeData


class LocalSubmanager(Submanager):
    def __init__(
        self,
        name: str,
        interface: Interface,
        settings: Any,
        state: Any,
    ):
        super().__init__(name)

        self.interface = interface
        self.settings = settings
        self.state = state

    async def update_database(self) -> None:
        await self.interface.update_database(self.settings, self.state)

    async def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
        meta_resolution_graphs: Mapping[str, MutableSequence[ResolutionGraph]],
    ) -> None:
        resolution_graphs = meta_resolution_graphs[self.name]

        async for resolution_graph in self.interface.resolve(
            self.settings,
            self.state,
            options,
            make_async_iterable(
                make_async_iterable(requirements) for requirements in requirements_list
            ),
        ):
            resolution_graphs.append(resolution_graph)

    async def fetch(
        self,
        submanagers: Mapping[str, Submanager],
        meta_options: Mapping[str, Options],
        package: Package,
        dependencies: Iterable[Dependency],
        nodes: Mapping[ManagerAndName, NodeData],
        packages_to_dependencies: Mapping[
            ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
        ],
        install_order: Iterable[tuple[ManagerAndName, NodeData]],
    ):
        options = meta_options.get(self.name)

        result = await self.interface.fetch(
            self.settings,
            self.state,
            options,
            package,
            make_async_iterable(dependencies),
            None,
            None,
        )

        if not isinstance(result, PackageIDAndInfo):
            with (
                TemporaryDirectory() as installation_path,
                TemporaryDirectory() as generators_path,
            ):
                subdependencies = packages_to_dependencies[
                    ManagerAndName(self.name, package.name)
                ]

                async with TaskGroup() as group:
                    group.create_task(
                        fetch_install(
                            submanagers,
                            install_order,
                            subdependencies,
                            installation_path,
                        )
                    )

                    group.create_task(
                        fetch_generate(
                            submanagers,
                            result,
                            subdependencies,
                            meta_options,
                            generators_path,
                        )
                    )

                result = await self.interface.fetch(
                    self.settings,
                    self.state,
                    options,
                    package,
                    make_async_iterable(dependencies),
                    installation_path,
                    generators_path,
                )

            if not isinstance(result, PackageIDAndInfo):
                raise Exception()

        id_and_info = result
        node = nodes[ManagerAndName(self.name, package.name)]
        node["product_id"] = id_and_info.product_id
        node["product_info"] = id_and_info.product_info

    async def install(self, id: str, installation_path: Path, product: Product) -> None:
        self.interface.install(self.settings, self.state, installation_path, product)

    async def install_init(self, installation_path: Path) -> str:
        return str(installation_path)

    async def install_send(
        self, source_id: str, destination: Submanager, destination_id: str | None
    ) -> str:
        return await destination.install_receive(destination_id, Path(source_id))

    async def install_receive(
        self, destination_id: str | None, installation_path: Path
    ) -> str:
        return str(installation_path)

    async def install_delete(self, id: str) -> None:
        pass

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None:
        await self.interface.generate(
            self.settings,
            self.state,
            options,
            make_async_iterable(products),
            make_async_iterable(generators),
            destination_path,
        )


@asynccontextmanager
async def LocalSubmanagerContext(
    name: str, config: SubmanagerLocalConfig
) -> AsyncGenerator[LocalSubmanager, None]:
    interface = type_cast(
        Interface,
        import_module(f"{config.package}.interface").interface,
    )

    async with interface.lifespan(config.settings) as state:
        yield LocalSubmanager(name, interface, config.settings, state)
