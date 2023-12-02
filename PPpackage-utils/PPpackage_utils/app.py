from asyncio import StreamWriter, TaskGroup
from asyncio import run as asyncio_run
from collections.abc import AsyncIterable, Awaitable, Callable, Coroutine
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import stderr
from traceback import print_exc
from typing import Any, Iterable, TypeVar

from typer import Typer

from .parse import (
    BuildResult,
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
    dump_bytes,
    dump_bytes_chunked,
    dump_loop,
    dump_many_async,
    load_bytes_chunked,
    load_loop,
    load_many,
    load_one,
)
from .utils import (
    TarFileInMemoryWrite,
    create_empty_tar,
    discard_async_iterable,
    ensure_dir_exists,
    get_standard_streams,
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


__debug = False

__app = AsyncTyper()


@__app.callback()
def callback(debug: bool = False) -> None:
    global __debug
    __debug = debug


RequirementTypeType = TypeVar("RequirementTypeType")


def init(
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
) -> Typer:
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

    return __app


def run(app: Typer, program_name: str) -> None:
    try:
        app()
    except Exception:
        print(f"{program_name}:", file=stderr)
        print_exc()

        exit(1)


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
