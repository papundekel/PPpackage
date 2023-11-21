from asyncio import run as asyncio_run
from collections.abc import AsyncIterable, Awaitable, Callable
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import stderr
from traceback import print_exc
from typing import Any, TypeVar

from typer import Typer

from .parse import (
    Dependency,
    FetchOutputValue,
    Options,
    Package,
    Product,
    ResolutionGraph,
    dump_many_async,
    load_impl,
    load_many,
    load_many_helper,
    load_one,
)
from .utils import ensure_dir_exists, get_standard_streams


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
        [bool, Path, Any, AsyncIterable[tuple[Package, AsyncIterable[Dependency]]]],
        AsyncIterable[FetchOutputValue],
    ],
    generate_callback: Callable[
        [
            bool,
            Path,
            Path,
            Any,
            AsyncIterable[Product],
            AsyncIterable[str],
        ],
        Awaitable[None],
    ],
    install_callback: Callable[
        [bool, Path, Path, Path, Path, AsyncIterable[Product]], Awaitable[None]
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
            async for _ in load_many_helper(__debug, stdin)
        )

        output = resolve_callback(__debug, cache_path, options, requirements_list)

        await dump_many_async(__debug, stdout, output)

    @__app.command()
    async def fetch(cache_path: Path) -> None:
        stdin, stdout = await get_standard_streams()

        options = await load_one(__debug, stdin, Options)

        packages = (
            (
                await load_impl(__debug, stdin, Package, length),
                load_many(__debug, stdin, Dependency),
            )
            async for length in load_many_helper(__debug, stdin)
        )

        output = fetch_callback(__debug, cache_path, options, packages)

        await dump_many_async(__debug, stdout, output)

    @__app.command()
    async def generate(cache_path: Path, generators_path: Path) -> None:
        stdin, _ = await get_standard_streams()

        options = await load_one(__debug, stdin, Options)
        products = load_many(__debug, stdin, Product)
        generators = load_many(__debug, stdin, str)

        await generate_callback(
            __debug, cache_path, generators_path, options, products, generators
        )

    @__app.command()
    async def install(
        cache_path: Path,
        destination_path: Path,
        pipe_from_sub_path: Path,
        pipe_to_sub_path: Path,
    ) -> None:
        ensure_dir_exists(destination_path)

        stdin, _ = await get_standard_streams()

        products = load_many(__debug, stdin, Product)

        await install_callback(
            __debug,
            cache_path,
            destination_path,
            pipe_from_sub_path,
            pipe_to_sub_path,
            products,
        )

    return __app


def run(app: Typer, program_name: str) -> None:
    try:
        app()
    except Exception:
        print(f"{program_name}:", file=stderr)
        print_exc()
        with open(f"/home/fackop/{program_name}.log", "w") as f:
            print_exc(file=f)

        exit(1)
