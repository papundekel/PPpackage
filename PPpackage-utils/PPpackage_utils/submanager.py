from asyncio import CancelledError, StreamReader, StreamWriter, get_running_loop
from asyncio import run as asyncio_run
from asyncio import start_unix_server
from collections.abc import AsyncIterable, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
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
from .utils import create_empty_tar, discard_async_iterable, get_standard_streams


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


__debug = False

__app = AsyncTyper()


@__app.callback()
def callback(debug: bool = False) -> None:
    global __debug
    __debug = debug


RequirementTypeType = TypeVar("RequirementTypeType")


def run(app: AsyncTyper, program_name: str) -> None:
    try:
        app()
    except Exception:
        print(f"{program_name}:", file=stderr)
        print_exc()

        exit(1)


def main(
    program_name: str,
    update_database_callback: Callable[[bool, Path], Awaitable[None]],
    resolve_callback: Callable[
        [bool, Path, Any, AsyncIterable[AsyncIterable[RequirementTypeType]]],
        AsyncIterable[ResolutionGraph],
    ],
    fetch_callback: Callable[
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
    ],
    generate_callback: Callable[
        [
            bool,
            Path,
            Any,
            AsyncIterable[Product],
            AsyncIterable[str],
        ],
        Awaitable[memoryview],
    ],
    install_callback: Callable[
        [bool, Path, Path, Path, memoryview, AsyncIterable[Product]],
        Awaitable[memoryview],
    ],
    RequirementType: type[RequirementTypeType],
) -> None:
    @__app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await update_database_callback(__debug, cache_path)

    @__app.command()
    async def resolve(cache_path: Path) -> None:
        stdin, stdout = await get_standard_streams()

        options = await load_one(__debug, stdin, Options)

        requirements_list = (
            load_many(__debug, stdin, RequirementType)
            async for _ in load_loop(__debug, stdin)
        )

        output = resolve_callback(__debug, cache_path, options, requirements_list)

        await dump_many_async(__debug, stdout, output)

    @__app.command()
    async def fetch(
        runner_path: Path, runner_workdir_path: Path, cache_path: Path
    ) -> None:
        stdin, stdout = await get_standard_streams()

        options = await load_one(__debug, stdin, Options)

        packages = (
            (
                await load_one(__debug, stdin, Package),
                load_many(__debug, stdin, Dependency),
            )
            async for _ in load_loop(__debug, stdin)
        )

        build_results = load_many(__debug, stdin, BuildResult)

        output, complete = fetch_callback(
            __debug,
            runner_path,
            runner_workdir_path,
            cache_path,
            options,
            packages,
            build_results,
        )

        await dump_many_async(__debug, stdout, output)

        await complete

    @__app.command()
    async def generate(cache_path: Path) -> None:
        stdin, stdout = await get_standard_streams()

        options = await load_one(__debug, stdin, Options)
        products = load_many(__debug, stdin, Product)
        generators = load_many(__debug, stdin, str)

        generators = await generate_callback(
            __debug, cache_path, options, products, generators
        )

        await dump_bytes_chunked(__debug, stdout, generators)

    @__app.command()
    async def install(
        cache_path: Path,
        runner_path: Path,
        runner_workdir_path: Path,
    ) -> None:
        stdin, stdout = await get_standard_streams()

        old_directory = await load_bytes_chunked(__debug, stdin)
        products = load_many(__debug, stdin, Product)

        new_directory = await install_callback(
            __debug,
            cache_path,
            runner_path,
            runner_workdir_path,
            old_directory,
            products,
        )

        await dump_bytes_chunked(__debug, stdout, new_directory)

    run(__app, program_name)


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
    runner_workdir_path: Path,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> tuple[AsyncIterable[PackageIDAndInfo], Awaitable[None]]:
    return (
        output
        async for output in send_callback(
            debug, runner_path, runner_workdir_path, cache_path, options, packages
        )
    ), discard_async_iterable(build_results)


async def run_server(
    debug: bool,
    program_name: str,
    run_path: Path,
    connection_handler: Callable[[bool, StreamReader, StreamWriter], Awaitable[None]],
):
    socket_path = run_path / f"{program_name}.sock"

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


async def main_server(
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
    try:
        with PidFile(program_name, piddir=run_path):
            async with connection_handler_context(debug) as connection_handler:
                await run_server(
                    debug,
                    program_name,
                    run_path,
                    connection_handler,
                )
    except PidFileAlreadyLockedError:
        print(f"{program_name} is already running.", file=stderr)
        raise Exit(1)
