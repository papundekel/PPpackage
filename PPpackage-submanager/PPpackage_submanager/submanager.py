from collections.abc import AsyncIterable, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

from PPpackage_utils.stream import Reader, Writer
from PPpackage_utils.tar import create_empty as create_empty_tar

from .schemes import (
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
)

RequirementTypeType = TypeVar("RequirementTypeType")
StateTypeType = TypeVar("StateTypeType")

UpdateDatabaseCallbackType = Callable[[bool, StateTypeType, Path], Awaitable[None]]
ResolveCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        AsyncIterable[AsyncIterable[RequirementTypeType]],
    ],
    AsyncIterable[ResolutionGraph],
]
FetchCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        Package,
        AsyncIterable[Dependency],
        memoryview | None,
        memoryview | None,
    ],
    Awaitable[PackageIDAndInfo | AsyncIterable[str]],
]

GenerateCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        AsyncIterable[Product],
        AsyncIterable[str],
    ],
    Awaitable[memoryview],
]
InstallPATCHCallbackType = Callable[
    [bool, StateTypeType, Path, str, Product],
    Awaitable[None],
]
InstallPOSTCallbackType = Callable[[bool, StateTypeType, memoryview], Awaitable[str]]
InstallPUTCallbackType = Callable[
    [bool, StateTypeType, str, memoryview], Awaitable[None]
]
InstallGETCallbackType = Callable[[bool, StateTypeType, str], Awaitable[memoryview]]
InstallDELETECallbackType = Callable[[bool, StateTypeType, str], Awaitable[None]]


@dataclass(frozen=True)
class Callbacks(Generic[RequirementTypeType, StateTypeType]):
    update_database: UpdateDatabaseCallbackType[StateTypeType]
    resolve: ResolveCallbackType[StateTypeType, RequirementTypeType]
    fetch: FetchCallbackType[StateTypeType]
    generate: GenerateCallbackType[StateTypeType]
    install_patch: InstallPATCHCallbackType[StateTypeType]
    install_post: InstallPOSTCallbackType[StateTypeType]
    install_put: InstallPUTCallbackType[StateTypeType]
    install_get: InstallGETCallbackType[StateTypeType]
    install_delete: InstallDELETECallbackType[StateTypeType]
    RequirementType: type[RequirementTypeType]


async def update_database(
    writer: Writer,
    update_database_callback: UpdateDatabaseCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
    cache_path: Path,
) -> None:
    await update_database_callback(debug, state, cache_path)


async def resolve(
    reader: Reader,
    writer: Writer,
    callback: ResolveCallbackType[StateTypeType, RequirementTypeType],
    RequirementType: type[RequirementTypeType],
    debug: bool,
    state: StateTypeType,
    cache_path: Path,
):
    options = await reader.load_one(Options)

    requirements_list = (
        reader.load_many(RequirementType) async for _ in reader.load_loop()
    )

    output = callback(debug, state, cache_path, options, requirements_list)

    await writer.dump_many_async(output)


async def fetch(
    reader: Reader,
    writer: Writer,
    callback: FetchCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
    cache_path: Path,
):
    options = await reader.load_one(Options)
    package = await reader.load_one(Package)
    installation_present = await reader.load_one(bool)
    installation = await reader.load_bytes_chunked() if installation_present else None
    generators_present = await reader.load_one(bool)
    generators = await reader.load_bytes_chunked() if generators_present else None
    dependencies = reader.load_many(Dependency)

    output = await callback(
        debug,
        state,
        cache_path,
        options,
        package,
        dependencies,
        installation,
        generators,
    )

    no_build = isinstance(output, PackageIDAndInfo)
    await writer.dump_one(no_build)

    if no_build:
        await writer.dump_one(output)
    else:
        await writer.dump_many_async(output)


async def generate(
    reader: Reader,
    writer: Writer,
    callback: GenerateCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
    cache_path: Path,
):
    options = await reader.load_one(Options)
    products = reader.load_many(Product)
    generators = reader.load_many(str)

    generators = await callback(debug, state, cache_path, options, products, generators)

    await writer.dump_bytes_chunked(generators)


async def install_patch(
    reader: Reader,
    writer: Writer,
    callback: InstallPATCHCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
    cache_path: Path,
):
    id = await reader.load_one(str)
    product = await reader.load_one(Product)

    await callback(debug, state, cache_path, id, product)


async def install_post(
    reader: Reader,
    writer: Writer,
    callback: InstallPOSTCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
):
    installation = await reader.load_bytes_chunked()

    id = await callback(debug, state, installation)

    await writer.dump_one(id)


async def install_put(
    reader: Reader,
    writer: Writer,
    callback: InstallPUTCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
):
    id = await reader.load_one(str)

    installation = await reader.load_bytes_chunked()

    await callback(debug, state, id, installation)


async def install_get(
    reader: Reader,
    writer: Writer,
    callback: InstallGETCallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
):
    id = await reader.load_one(str)

    installation = await callback(debug, state, id)

    await writer.dump_bytes_chunked(installation)


async def install_delete(
    reader: Reader,
    writer: Writer,
    callback: InstallDELETECallbackType[StateTypeType],
    debug: bool,
    state: StateTypeType,
):
    id = await reader.load_one(str)

    await callback(debug, state, id)


async def generate_empty(
    debug: bool,
    data: Any,
    cache_path: Path,
    options: Any,
    products: AsyncIterable[Product],
    generators: AsyncIterable[str],
) -> memoryview:
    async for _ in products:
        pass

    async for _ in generators:
        pass

    return create_empty_tar()


@contextmanager
def noop_session_lifetime(debug: bool, data: Any):
    yield None


async def update_database_noop(debug: bool, data: Any, cache_path: Path) -> None:
    pass
