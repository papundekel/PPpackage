from asyncio import run as asyncio_run
from collections.abc import AsyncIterable, Awaitable, Callable, Iterable
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import exit, stderr
from typing import Any, TypeVar

from typer import Typer

from .parse import (
    FetchOutputValue,
    GenerateInput,
    Options,
    PackageWithDependencies,
    Product,
    ResolutionGraph,
    ResolveInput,
    dump_one,
    load_many,
    load_one,
)
from .utils import MyException, ensure_dir_exists, get_standard_streams


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
    update_database_callback: Callable[[Path], Awaitable[None]],
    resolve_callback: Callable[
        [Path, Any, Iterable[Iterable[RequirementTypeType]]],
        Awaitable[Iterable[ResolutionGraph]],
    ],
    fetch_callback: Callable[
        [Path, Any, AsyncIterable[PackageWithDependencies]],
        Awaitable[Iterable[FetchOutputValue]],
    ],
    generate_callback: Callable[
        [
            Path,
            Path,
            Any,
            Iterable[Product],
            Iterable[str],
        ],
        Awaitable[None],
    ],
    install_callback: Callable[
        [Path, Path, Path, Path, AsyncIterable[Product]], Awaitable[None]
    ],
    RequirementType: type[RequirementTypeType],
) -> Typer:
    @__app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await update_database_callback(cache_path)

    @__app.command()
    async def resolve(cache_path: Path) -> None:
        stdin, stdout = await get_standard_streams()

        input = await load_one(stdin, ResolveInput[RequirementType])

        output = await resolve_callback(
            cache_path, input.options, input.requirements_list
        )

        await dump_one(__debug, stdout, output)

    @__app.command()
    async def fetch(cache_path: Path) -> None:
        stdin, stdout = await get_standard_streams()

        options = await load_one(stdin, Options)
        packages = load_many(stdin, PackageWithDependencies)

        output = await fetch_callback(cache_path, options, packages)

        await dump_one(__debug, stdout, output)

    @__app.command()
    async def generate(cache_path: Path, generators_path: Path) -> None:
        stdin, _ = await get_standard_streams()

        input = await load_one(stdin, GenerateInput)

        await generate_callback(
            cache_path,
            generators_path,
            input.options,
            input.products,
            input.generators,
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

        products = load_many(stdin, Product)

        await install_callback(
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
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"{program_name}: {e}", file=stderr)
        exit(1)
