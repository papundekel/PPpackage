from asyncio import run as asyncio_run
from collections.abc import Awaitable, Callable, Iterable, Mapping, Set
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import exit, stderr, stdin, stdout
from typing import Any

from typer import Typer

from .utils import (
    MyException,
    Product,
    ensure_dir_exists,
    json_dump,
    json_load,
    parse_fetch_input,
    parse_resolve_input,
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


def init(
    database_updater: Callable[[Path], Awaitable[None]],
    resolver: Callable[[Path, Set[Any], Any], Awaitable[Iterable[Mapping[str, str]]]],
    fetcher: Callable[
        [Path, Mapping[str, str], Any, Set[str], Path],
        Awaitable[Mapping[str, str]],
    ],
    installer: Callable[[Path, Set[Product], Path, Path, Path], Awaitable[None]],
    requirements_parser: Callable[[Any], Set[Any]],
    options_parser: Callable[[Any], Any],
    lockfile_parser: Callable[[Any], Mapping[str, str]],
    products_parser: Callable[[Any], Set[Product]],
) -> Typer:
    @__app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await database_updater(cache_path)

    @__app.command()
    async def resolve(cache_path: Path) -> None:
        input = json_load(stdin)

        requirements, options = parse_resolve_input(
            requirements_parser, options_parser, input
        )

        lockfiles = await resolver(cache_path, requirements, options)

        indent = 4 if __debug else None

        json_dump(lockfiles, stdout, indent=indent)

    @__app.command()
    async def fetch(cache_path: Path, generators_path: Path) -> None:
        input = json_load(stdin)

        lockfile, options, generators = parse_fetch_input(
            lockfile_parser, options_parser, input
        )

        product_ids = await fetcher(
            cache_path, lockfile, options, generators, generators_path
        )

        indent = 4 if __debug else None

        json_dump(product_ids, stdout, indent=indent)

    @__app.command()
    async def install(
        cache_path: Path,
        destination_path: Path,
        pipe_from_sub_path: Path,
        pipe_to_sub_path: Path,
    ) -> None:
        input = json_load(stdin)

        ensure_dir_exists(destination_path)

        products = products_parser(input)

        await installer(
            cache_path, products, destination_path, pipe_from_sub_path, pipe_to_sub_path
        )

    return __app


def run(app: Typer, program_name: str) -> None:
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"{program_name}: {e}", file=stderr)
        exit(1)
