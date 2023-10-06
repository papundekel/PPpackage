from asyncio import run as asyncio_run
from collections.abc import Awaitable, Callable, Iterable, Mapping, Set
from functools import partial, wraps
from inspect import iscoroutinefunction
from json import dump as json_dump
from json import load as json_load
from pathlib import Path
from sys import exit, stderr, stdin, stdout
from typing import Any

from typer import Typer

from .utils import (
    MyException,
    Product,
    ensure_dir_exists,
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


_debug = False

app = AsyncTyper()


@app.callback()
def callback(debug: bool = False) -> None:
    global _debug
    _debug = debug


def init(
    database_updater: Callable[[Path], Awaitable[None]],
    submanagers_handler: Callable[[], Awaitable[Iterable[str]]],
    resolver: Callable[
        [Path, Iterable[Any], Any], Awaitable[Iterable[Mapping[str, str]]]
    ],
    fetcher: Callable[
        [Path, Mapping[str, str], Any, Set[str], Path],
        Awaitable[Mapping[str, str]],
    ],
    installer: Callable[[Path, Set[Product], Path, Path, Path], Awaitable[None]],
    requirements_parser: Callable[[Any], Iterable[Any]],
    options_parser: Callable[[Any], Any],
    lockfile_parser: Callable[[Any], Mapping[str, str]],
    products_parser: Callable[[Any], Set[Product]],
) -> None:
    @app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await database_updater(cache_path)

    @app.command()
    async def submanagers() -> None:
        submanagers = await submanagers_handler()

        json_dump(submanagers, stdout)

    @app.command()
    async def resolve(cache_path: Path) -> None:
        input = json_load(stdin)

        requirements, options = parse_resolve_input(
            requirements_parser, options_parser, input
        )

        lockfiles = await resolver(cache_path, requirements, options)

        indent = 4 if _debug else None

        json_dump(lockfiles, stdout, indent=indent)

    @app.command()
    async def fetch(cache_path: Path, generators_path: Path) -> None:
        input = json_load(stdin)

        lockfile, options, generators = parse_fetch_input(
            lockfile_parser, options_parser, input
        )

        product_ids = await fetcher(
            cache_path, lockfile, options, generators, generators_path
        )

        indent = 4 if _debug else None

        json_dump(product_ids, stdout, indent=indent)

    @app.command()
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


def run(manager_id: str) -> None:
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"{manager_id}: {e}", file=stderr)
        exit(1)