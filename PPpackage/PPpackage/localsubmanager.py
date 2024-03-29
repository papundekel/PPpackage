from collections.abc import AsyncGenerator, Iterable, Mapping, Set
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterable, TypeVar
from typing import cast as type_cast

from PPpackage_submanager.interface import Interface, load_interface_module
from PPpackage_submanager.schemes import (
    Dependency,
    FetchRequest,
    Lock,
    Options,
    Package,
    Product,
    ProductIDAndInfo,
    ResolutionGraph,
)
from PPpackage_utils.tar import extract as tar_extract
from PPpackage_utils.utils import make_async_iterable
from PPpackage_utils.validation import load_object
from pydantic import BaseModel

from .schemes import LocalSubmanagerConfig
from .submanager import Submanager

RequirementType = TypeVar("RequirementType")


async def make_async_requirements(
    Requirement: type[RequirementType], requirements: Iterable[Any]
) -> AsyncIterable[RequirementType]:
    for requirement in requirements:
        yield load_object(Requirement, requirement)


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

    def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
        locks: Mapping[str, str],
    ) -> AsyncIterable[ResolutionGraph]:
        return self.interface.resolve(
            self.settings,
            self.state,
            options,
            make_async_iterable(
                make_async_requirements(self.interface.Requirement, requirements)
                for requirements in requirements_list
            ),
            make_async_iterable(Lock(name, version) for name, version in locks.items()),
        )

    @asynccontextmanager
    async def fetch(
        self,
        options: Options,
        package: Package,
        dependencies: Iterable[Dependency],
        installation_path: Path | None,
        generators_path: Path | None,
    ) -> AsyncGenerator[ProductIDAndInfo | FetchRequest, None]:
        yield await self.interface.fetch(
            self.settings,
            self.state,
            options,
            package,
            make_async_iterable(dependencies),
            installation_path,
            generators_path,
        )

    async def install(self, id: str, installation_path: Path, product: Product) -> None:
        await self.interface.install(
            self.settings, self.state, installation_path, product
        )

    async def install_init(self, installation_path: Path) -> str:
        return str(installation_path)

    async def install_send(
        self,
        source_id: str,
        destination: Submanager,
        destination_id: str | None,
        installation_path: Path,
    ) -> str:
        return await destination.install_receive(
            destination_id, None, installation_path
        )

    async def install_receive(
        self,
        destination_id: str | None,
        installation: memoryview | None,
        installation_path: Path,
    ) -> str:
        if installation is not None:
            tar_extract(installation, installation_path)

        return str(installation_path)

    async def install_download(self, id: str, installation_path: Path) -> None:
        pass

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
    name: str, config: LocalSubmanagerConfig
) -> AsyncGenerator[LocalSubmanager, None]:
    interface = load_interface_module(config.package)

    settings = load_object(
        type_cast(type[BaseModel], interface.Settings), config.settings
    )

    async with interface.lifespan(settings) as state:
        yield LocalSubmanager(name, interface, settings, state)
