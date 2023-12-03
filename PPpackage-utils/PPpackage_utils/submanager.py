from asyncio import CancelledError, StreamReader, StreamWriter, get_running_loop
from asyncio import run as asyncio_run
from asyncio import start_unix_server
from collections.abc import AsyncIterable, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from signal import SIGTERM
from sys import stderr
from traceback import print_exc
from typing import Any, TypeVar

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
    load_bytes_chunked,
    load_loop,
    load_many,
    load_one,
)
from .utils import Phase, create_empty_tar, discard_async_iterable, get_standard_streams


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
UpdateDatabaseCallbackType = Callable[[bool, Path], Awaitable[None]]
ResolveCallbackType = Callable[
    [bool, Path, Any, AsyncIterable[AsyncIterable[RequirementTypeType]]],
    AsyncIterable[ResolutionGraph],
]
FetchCallbackType = Callable[
    [
        bool,
        Path,
        Path,
        Path,
        Any,
        AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
        AsyncIterable[BuildResult],
    ],
    tuple[AsyncIterable[PackageIDAndInfo], Awaitable[None]],
]
GenerateCallbackType = Callable[
    [bool, Path, Any, AsyncIterable[Product], AsyncIterable[str]], Awaitable[memoryview]
]
InstallCallbackType = Callable[
    [bool, Path, Path, Path, memoryview, AsyncIterable[Product]], Awaitable[memoryview]
]


def run(app: AsyncTyper, program_name: str) -> None:
    try:
        app()
    except Exception:
        print(f"{program_name}:", file=stderr)
        print_exc()

        exit(1)


async def update_database(
    update_database_callback: UpdateDatabaseCallbackType, debug: bool, cache_path: Path
) -> None:
    await update_database_callback(debug, cache_path)


async def resolve(
    reader: StreamReader,
    writer: StreamWriter,
    callback: ResolveCallbackType[RequirementTypeType],
    RequirementType: type[RequirementTypeType],
    debug: bool,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)

    requirements_list = (
        load_many(debug, reader, RequirementType)
        async for _ in load_loop(debug, reader)
    )

    output = callback(debug, cache_path, options, requirements_list)

    await dump_many_async(debug, writer, output)


async def fetch(
    reader: StreamReader,
    writer: StreamWriter,
    callback: FetchCallbackType,
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
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
        debug,
        runner_path,
        runner_workdirs_path,
        cache_path,
        options,
        packages,
        build_results,
    )

    await dump_many_async(debug, writer, output)

    await complete


async def generate(
    reader: StreamReader,
    writer: StreamWriter,
    callback: GenerateCallbackType,
    debug: bool,
    cache_path: Path,
):
    options = await load_one(debug, reader, Options)
    products = load_many(debug, reader, Product)
    generators = load_many(debug, reader, str)

    generators = await callback(debug, cache_path, options, products, generators)

    await dump_bytes_chunked(debug, writer, generators)


async def install(
    reader: StreamReader,
    writer: StreamWriter,
    callback: InstallCallbackType,
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
):
    old_directory = await load_bytes_chunked(debug, reader)
    products = load_many(debug, reader, Product)

    new_directory = await callback(
        debug, cache_path, runner_path, runner_workdirs_path, old_directory, products
    )

    await dump_bytes_chunked(debug, writer, new_directory)


async def handle_connection(
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
    update_database_callback: UpdateDatabaseCallbackType,
    resolve_callback: ResolveCallbackType[RequirementTypeType],
    fetch_callback: FetchCallbackType,
    generate_callback: GenerateCallbackType,
    install_callback: InstallCallbackType,
    RequirementType: type[RequirementTypeType],
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
):
    while True:
        phase = await load_one(debug, reader, Phase)

        match phase:
            case Phase.UPDATE_DATABASE:
                await update_database(update_database_callback, debug, cache_path)
            case Phase.RESOLVE:
                await resolve(
                    reader, writer, resolve_callback, RequirementType, debug, cache_path
                )
            case Phase.FETCH:
                await fetch(
                    reader,
                    writer,
                    fetch_callback,
                    debug,
                    cache_path,
                    runner_path,
                    runner_workdirs_path,
                )
            case Phase.GENERATE:
                await generate(reader, writer, generate_callback, debug, cache_path)
            case Phase.INSTALL:
                await install(
                    reader,
                    writer,
                    install_callback,
                    debug,
                    cache_path,
                    runner_path,
                    runner_workdirs_path,
                )
            case Phase.END:
                break


@asynccontextmanager
async def submanager_context(
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
    update_database_callback: UpdateDatabaseCallbackType,
    resolve_callback: ResolveCallbackType[RequirementTypeType],
    fetch_callback: FetchCallbackType,
    generate_callback: GenerateCallbackType,
    install_callback: InstallCallbackType,
    RequirementType: type[RequirementTypeType],
    debug: bool,
):
    yield partial(
        handle_connection,
        cache_path,
        runner_path,
        runner_workdirs_path,
        update_database_callback,
        resolve_callback,
        fetch_callback,
        generate_callback,
        install_callback,
        RequirementType,
    )


def submanager__main__(program_name: str, main_f) -> None:
    @__app.command()
    async def main_commmand(
        run_path: Path,
        cache_path: Path,
        runner_path: Path,
        runner_workdirs_path: Path,
        debug: bool = False,
    ):
        await main_f(debug, run_path, cache_path, runner_path, runner_workdirs_path)

    run(__app, program_name)


async def submanager_main(
    update_database_callback: UpdateDatabaseCallbackType,
    resolve_callback: ResolveCallbackType[RequirementTypeType],
    fetch_callback: FetchCallbackType,
    generate_callback: GenerateCallbackType,
    install_callback: InstallCallbackType,
    RequirementType: type[RequirementTypeType],
    program_name: str,
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
):
    await run_server(
        debug,
        program_name,
        run_path,
        partial(
            submanager_context,
            cache_path,
            runner_path,
            runner_workdirs_path,
            update_database_callback,
            resolve_callback,
            fetch_callback,
            generate_callback,
            install_callback,
            RequirementType,
        ),
    )


async def generate_empty(
    debug: bool,
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
            Path,
            Path,
            Path,
            Any,
            AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
        ],
        AsyncIterable[PackageIDAndInfo],
    ],
    debug: bool,
    runner_path: Path,
    runner_workdirs_path: Path,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> tuple[AsyncIterable[PackageIDAndInfo], Awaitable[None]]:
    return (
        output
        async for output in send_callback(
            debug, runner_path, runner_workdirs_path, cache_path, options, packages
        )
    ), discard_async_iterable(build_results)


async def run_server(
    debug: bool,
    program_name: str,
    run_path: Path,
    connection_handler_context: Callable[
        [bool],
        AbstractAsyncContextManager[
            Callable[[bool, StreamReader, StreamWriter], Awaitable[None]]
        ],
    ],
):
    socket_path = run_path / f"{program_name}.sock"

    try:
        with PidFile(program_name, run_path):
            async with connection_handler_context(debug) as connection_handler:
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
