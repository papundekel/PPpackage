from ast import Call
from asyncio import CancelledError, StreamReader, StreamWriter, get_running_loop
from asyncio import run as asyncio_run
from asyncio import start_unix_server
from collections.abc import AsyncIterable, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from signal import SIGTERM
from sys import stderr
from traceback import print_exc
from typing import Any, Generic, TypeVar

from pid import PidFile, PidFileAlreadyLockedError
from typer import Exit, Typer

from .parse import (
    BuildResult,
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
    dump_bytes_chunked,
    dump_many_async,
    dump_one,
    load_bytes_chunked,
    load_loop,
    load_many,
    load_one,
)
from .utils import (
    MyException,
    RunnerInfo,
    SubmanagerCommand,
    create_empty_tar,
    discard_async_iterable,
)


class AsyncTyper(Typer):
    @staticmethod
    def maybe_run_async(decorator: Callable[[Any], Any], f: Any) -> Any:
        if iscoroutinefunction(f):

            @wraps(f)
            def runner(*args: Any, **kwargs: Any) -> Any:
                return asyncio_run(f(*args, **kwargs))

            decorator(runner)
        else:
            decorator(f)
        return f

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        decorator = super().callback(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)

    def command(self, *args: Any, **kwargs: Any) -> Any:
        decorator = super().command(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)


__app = AsyncTyper()

RequirementTypeType = TypeVar("RequirementTypeType")
DataTypeType = TypeVar("DataTypeType")

UpdateDatabaseCallbackType = Callable[[bool, DataTypeType, Path], Awaitable[None]]
ResolveCallbackType = Callable[
    [
        bool,
        DataTypeType,
        Path,
        Any,
        AsyncIterable[AsyncIterable[RequirementTypeType]],
    ],
    AsyncIterable[ResolutionGraph],
]
FetchCallbackType = Callable[
    [
        bool,
        DataTypeType,
        Path,
        Any,
        AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
        AsyncIterable[BuildResult],
    ],
    tuple[AsyncIterable[PackageIDAndInfo], Awaitable[None]],
]
GenerateCallbackType = Callable[
    [bool, DataTypeType, Path, Any, AsyncIterable[Product], AsyncIterable[str]],
    Awaitable[memoryview],
]
InstallCallbackType = Callable[
    [bool, DataTypeType, Path, memoryview, AsyncIterable[Product]],
    Awaitable[memoryview],
]


@dataclass(frozen=True)
class SubmanagerCallbacks(Generic[RequirementTypeType, DataTypeType]):
    update_database: UpdateDatabaseCallbackType[DataTypeType]
    resolve: ResolveCallbackType[DataTypeType, RequirementTypeType]
    fetch: FetchCallbackType[DataTypeType]
    generate: GenerateCallbackType[DataTypeType]
    install: InstallCallbackType[DataTypeType]
    RequirementType: type[RequirementTypeType]


LifetimeReturnType = AbstractAsyncContextManager[
    Callable[[bool, StreamReader, StreamWriter], Awaitable[None]]
]


def run(app: AsyncTyper, program_name: str) -> None:
    try:
        app()
    except Exception:
        print(f"{program_name}:", file=stderr)
        print_exc()

        exit(1)


async def update_database(
    update_database_callback: UpdateDatabaseCallbackType,
    debug: bool,
    data: Any,
    cache_path: Path,
) -> None:
    await update_database_callback(debug, data, cache_path)


async def resolve(
    reader: StreamReader,
    writer: StreamWriter,
    callback: ResolveCallbackType[DataTypeType, RequirementTypeType],
    RequirementType: type[RequirementTypeType],
    debug: bool,
    data: Any,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)

    requirements_list = (
        load_many(debug, reader, RequirementType)
        async for _ in load_loop(debug, reader)
    )

    output = callback(debug, data, cache_path, options, requirements_list)

    await dump_many_async(debug, writer, output)


async def fetch(
    reader: StreamReader,
    writer: StreamWriter,
    callback: FetchCallbackType,
    debug: bool,
    data: Any,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)

    packages = (
        (
            await load_one(debug, reader, Package),
            load_many(debug, reader, Dependency),
        )
        async for _ in load_loop(debug, reader)
    )

    build_results = load_many(debug, reader, BuildResult)

    output, complete = callback(
        debug, data, cache_path, options, packages, build_results
    )

    await dump_many_async(debug, writer, output)

    await complete


async def generate(
    reader: StreamReader,
    writer: StreamWriter,
    callback: GenerateCallbackType,
    debug: bool,
    data: Any,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)
    products = load_many(debug, reader, Product)
    generators = load_many(debug, reader, str)

    generators = await callback(debug, data, cache_path, options, products, generators)

    await dump_bytes_chunked(debug, writer, generators)


async def install(
    reader: StreamReader,
    writer: StreamWriter,
    callback: InstallCallbackType,
    debug: bool,
    data: Any,
    cache_path: Path,
    old_directory: memoryview,
) -> memoryview:
    products = load_many(debug, reader, Product)

    new_directory = await callback(debug, data, cache_path, old_directory, products)

    await dump_one(debug, writer, None)

    return new_directory


async def install_upload(debug: bool, reader: StreamReader):
    return await load_bytes_chunked(debug, reader)


async def install_download(debug: bool, writer: StreamWriter, installation: memoryview):
    await dump_bytes_chunked(debug, writer, installation)


async def handle_connection(
    cache_path: Path,
    callbacks: SubmanagerCallbacks,
    data: Any,
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
):
    installation: memoryview | None = None

    while True:
        phase = await load_one(debug, reader, SubmanagerCommand)

        match phase:
            case SubmanagerCommand.UPDATE_DATABASE:
                await update_database(
                    callbacks.update_database, debug, data, cache_path
                )
            case SubmanagerCommand.RESOLVE:
                await resolve(
                    reader,
                    writer,
                    callbacks.resolve,
                    callbacks.RequirementType,
                    debug,
                    data,
                    cache_path,
                )
            case SubmanagerCommand.FETCH:
                await fetch(
                    reader,
                    writer,
                    callbacks.fetch,
                    debug,
                    data,
                    cache_path,
                )
            case SubmanagerCommand.GENERATE:
                await generate(
                    reader, writer, callbacks.generate, debug, data, cache_path
                )
            case SubmanagerCommand.INSTALL:
                if installation is None:
                    raise MyException("Installation not initialized. First upload one.")

                installation = await install(
                    reader,
                    writer,
                    callbacks.install,
                    debug,
                    data,
                    cache_path,
                    installation,
                )

            case SubmanagerCommand.INSTALL_UPLOAD:
                installation = await install_upload(debug, reader)
            case SubmanagerCommand.INSTALL_DOWNLOAD:
                if installation is None:
                    raise MyException("Installation not initialized. First upload one.")

                await install_download(debug, writer, installation)
            case SubmanagerCommand.END:
                break


def submanager__main__runner(program_name: str, main_f: Callable) -> None:
    @__app.command()
    async def main_commmand(
        run_path: Path,
        cache_path: Path,
        runner_path: Path,
        runner_workdirs_path: Path,
        debug: bool = False,
    ):
        await main_f(
            debug, run_path, cache_path, RunnerInfo(runner_path, runner_workdirs_path)
        )

    run(__app, program_name)


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


def fetch_receive_discard(
    send_callback: Callable[
        [
            bool,
            DataTypeType,
            Path,
            Any,
            AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
        ],
        AsyncIterable[PackageIDAndInfo],
    ],
    debug: bool,
    data: DataTypeType,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> tuple[AsyncIterable[PackageIDAndInfo], Awaitable[None]]:
    return (
        output
        async for output in send_callback(
            debug,
            data,
            cache_path,
            options,
            packages,
        )
    ), discard_async_iterable(build_results)


async def run_server(
    debug: bool,
    program_name: str,
    run_path: Path,
    lifetime: Callable[[bool], LifetimeReturnType],
):
    socket_path = run_path / f"{program_name}.sock"

    try:
        with PidFile(program_name, run_path):
            async with lifetime(debug) as connection_handler:
                try:
                    async with await start_unix_server(
                        partial(connection_handler, debug), socket_path
                    ) as server:
                        await server.start_serving()

                        loop = get_running_loop()

                        future = loop.create_future()

                        loop.add_signal_handler(SIGTERM, lambda: future.cancel())

                        await future
                except CancelledError:
                    pass
                finally:
                    socket_path.unlink()
    except PidFileAlreadyLockedError:
        print(f"{program_name} is already running.", file=stderr)
        raise Exit(1)
