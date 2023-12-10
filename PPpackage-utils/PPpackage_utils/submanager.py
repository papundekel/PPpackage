from asyncio import CancelledError, StreamReader, StreamWriter, get_running_loop
from asyncio import run as asyncio_run
from asyncio import start_unix_server
from collections.abc import AsyncIterable, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from signal import SIGTERM
from sys import stderr
from token import OP
from traceback import print_exc
from typing import Any, ContextManager, Generic, TypeVar

from pid import PidFile, PidFileAlreadyLockedError
from typer import Exit, Typer

from .parse import BuildResult as BuildResultParse
from .parse import (
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
    dump_bytes_chunked,
    dump_loop_async,
    dump_many_async,
    dump_one,
    load_bytes_chunked,
    load_loop,
    load_many,
    load_one,
)
from .utils import (
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


BuildRequest = tuple[str, AsyncIterable[str]]


@dataclass(frozen=True)
class BuildResult:
    name: str
    is_installation: bool
    data: memoryview


__app = AsyncTyper()

RequirementTypeType = TypeVar("RequirementTypeType")
DataTypeType = TypeVar("DataTypeType")
SessionDataTypeType = TypeVar("SessionDataTypeType")

UpdateDatabaseCallbackType = Callable[
    [bool, DataTypeType, SessionDataTypeType, Path], Awaitable[None]
]
ResolveCallbackType = Callable[
    [
        bool,
        DataTypeType,
        SessionDataTypeType,
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
        SessionDataTypeType,
        Path,
        Any,
        AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
        AsyncIterable[BuildResult],
    ],
    AsyncIterable[PackageIDAndInfo | BuildRequest],
]

GenerateCallbackType = Callable[
    [
        bool,
        DataTypeType,
        SessionDataTypeType,
        Path,
        Any,
        AsyncIterable[Product],
        AsyncIterable[str],
    ],
    Awaitable[memoryview],
]
InstallCallbackType = Callable[
    [bool, DataTypeType, SessionDataTypeType, Path, AsyncIterable[Product]],
    Awaitable[None],
]
InstallUploadCallbackType = Callable[
    [bool, DataTypeType, SessionDataTypeType, memoryview], Awaitable[None]
]
InstallDownloadCallbackType = Callable[
    [bool, DataTypeType, SessionDataTypeType], Awaitable[memoryview]
]


@dataclass(frozen=True)
class SubmanagerCallbacks(
    Generic[RequirementTypeType, DataTypeType, SessionDataTypeType]
):
    update_database: UpdateDatabaseCallbackType[DataTypeType, SessionDataTypeType]
    resolve: ResolveCallbackType[DataTypeType, SessionDataTypeType, RequirementTypeType]
    fetch: FetchCallbackType[DataTypeType, SessionDataTypeType]
    generate: GenerateCallbackType[DataTypeType, SessionDataTypeType]
    install: InstallCallbackType[DataTypeType, SessionDataTypeType]
    install_upload: InstallUploadCallbackType[DataTypeType, SessionDataTypeType]
    install_download: InstallDownloadCallbackType[DataTypeType, SessionDataTypeType]
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


class SubmanagerCommandFailure(Exception):
    pass


@asynccontextmanager
async def write_success(debug: bool, writer: StreamWriter):
    try:
        yield
        success = True
    except SubmanagerCommandFailure:
        success = False

    await dump_one(debug, writer, success)


async def update_database(
    writer: StreamWriter,
    update_database_callback: UpdateDatabaseCallbackType[
        DataTypeType, SessionDataTypeType
    ],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
    cache_path: Path,
) -> None:
    async with write_success(debug, writer):
        await update_database_callback(debug, data, session_data, cache_path)


async def resolve(
    reader: StreamReader,
    writer: StreamWriter,
    callback: ResolveCallbackType[
        DataTypeType, SessionDataTypeType, RequirementTypeType
    ],
    RequirementType: type[RequirementTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)

    requirements_list = (
        load_many(debug, reader, RequirementType)
        async for _ in load_loop(debug, reader)
    )

    async with write_success(debug, writer):
        output = callback(
            debug, data, session_data, cache_path, options, requirements_list
        )

        await dump_many_async(debug, writer, output)


async def fetch(
    reader: StreamReader,
    writer: StreamWriter,
    callback: FetchCallbackType[DataTypeType, SessionDataTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
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

    build_results = (
        BuildResult(
            (build_result := await load_one(debug, reader, BuildResultParse)).name,
            build_result.is_root,
            await load_bytes_chunked(debug, reader),
        )
        async for _ in load_loop(debug, reader)
    )

    async with write_success(debug, writer):
        output = callback(
            debug,
            data,
            session_data,
            cache_path,
            options,
            packages,
            build_results,
        )

        async for message in dump_loop_async(debug, writer, output):
            is_id_and_info = isinstance(message, PackageIDAndInfo)

            await dump_one(debug, writer, is_id_and_info)

            if is_id_and_info:
                await dump_one(debug, writer, message)
            else:
                package_name, generators = message
                await dump_one(debug, writer, package_name)
                await dump_many_async(debug, writer, generators)


async def generate(
    reader: StreamReader,
    writer: StreamWriter,
    callback: GenerateCallbackType[DataTypeType, SessionDataTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)
    products = load_many(debug, reader, Product)
    generators = load_many(debug, reader, str)

    async with write_success(debug, writer):
        generators = await callback(
            debug, data, session_data, cache_path, options, products, generators
        )

    await dump_bytes_chunked(debug, writer, generators)


async def install(
    reader: StreamReader,
    writer: StreamWriter,
    callback: InstallCallbackType[DataTypeType, SessionDataTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
    cache_path: Path,
):
    products = load_many(debug, reader, Product)

    async with write_success(debug, writer):
        await callback(debug, data, session_data, cache_path, products)


async def install_upload(
    reader: StreamReader,
    callback: InstallUploadCallbackType[DataTypeType, SessionDataTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
):
    installation = await load_bytes_chunked(debug, reader)

    await callback(debug, data, session_data, installation)


async def install_download(
    writer: StreamWriter,
    callback: InstallDownloadCallbackType[DataTypeType, SessionDataTypeType],
    debug: bool,
    data: DataTypeType,
    session_data: SessionDataTypeType,
):
    installation = await callback(debug, data, session_data)

    await dump_bytes_chunked(debug, writer, installation)


async def handle_connection(
    cache_path: Path,
    callbacks: SubmanagerCallbacks,
    data: DataTypeType,
    SessionLifetime: Callable[[bool, DataTypeType], ContextManager],
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
):
    with SessionLifetime(debug, data) as session_data:
        while True:
            phase = await load_one(debug, reader, SubmanagerCommand)

            match phase:
                case SubmanagerCommand.UPDATE_DATABASE:
                    await update_database(
                        writer,
                        callbacks.update_database,
                        debug,
                        data,
                        session_data,
                        cache_path,
                    )
                case SubmanagerCommand.RESOLVE:
                    await resolve(
                        reader,
                        writer,
                        callbacks.resolve,
                        callbacks.RequirementType,
                        debug,
                        data,
                        session_data,
                        cache_path,
                    )
                case SubmanagerCommand.FETCH:
                    await fetch(
                        reader,
                        writer,
                        callbacks.fetch,
                        debug,
                        data,
                        session_data,
                        cache_path,
                    )
                case SubmanagerCommand.GENERATE:
                    await generate(
                        reader,
                        writer,
                        callbacks.generate,
                        debug,
                        data,
                        session_data,
                        cache_path,
                    )
                case SubmanagerCommand.INSTALL:
                    await install(
                        reader,
                        writer,
                        callbacks.install,
                        debug,
                        data,
                        session_data,
                        cache_path,
                    )

                case SubmanagerCommand.INSTALL_UPLOAD:
                    await install_upload(
                        reader, callbacks.install_upload, debug, data, session_data
                    )
                case SubmanagerCommand.INSTALL_DOWNLOAD:
                    await install_download(
                        writer, callbacks.install_download, debug, data, session_data
                    )
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
    session_data: Any,
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


@contextmanager
def noop_session_lifetime(debug: bool, data: Any):
    yield None


async def update_database_noop(
    debug: bool, data: Any, session_data: Any, cache_path: Path
) -> None:
    pass


@asynccontextmanager
async def discard_build_results_context(build_results: AsyncIterable[BuildResult]):
    try:
        yield
    finally:
        await discard_async_iterable(build_results)
