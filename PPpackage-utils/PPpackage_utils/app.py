from asyncio import run as asyncio_run
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import exit, stderr, stdin, stdout
from typing import Any

from PPpackage_utils.parse import (
    FetchInput,
    FetchOutput,
    GenerateInputPackagesValue,
    parse_generate_input,
    parse_resolve_input,
)
from typer import Typer

from .utils import (
    MyException,
    Product,
    ResolutionGraph,
    ensure_dir_exists,
    json_dump,
    json_dumps,
    json_load,
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
    update_database_callback: Callable[[Path], Awaitable[None]],
    resolve_callback: Callable[
        [Path, Sequence[Set[Any]], Any], Awaitable[Set[ResolutionGraph]]
    ],
    fetch_callback: Callable[[Path, FetchInput], Awaitable[FetchOutput]],
    generate_callback: Callable[
        [
            Path,
            Set[str],
            Path,
            Any,
            Mapping[str, GenerateInputPackagesValue],
        ],
        Awaitable[None],
    ],
    install_callback: Callable[[Path, Set[Product], Path, Path, Path], Awaitable[None]],
    requirements_parser: Callable[[bool, Any], Set[Any]],
    options_parser: Callable[[bool, Any], Any],
    products_parser: Callable[[bool, Any], Set[Product]],
) -> Typer:
    @__app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await update_database_callback(cache_path)

    @__app.command()
    async def resolve(cache_path: Path) -> None:
        input = json_load(stdin)

        requirements_list, options = parse_resolve_input(
            __debug, requirements_parser, options_parser, input
        )

        resolution_graphs = await resolve_callback(
            cache_path, requirements_list, options
        )

        if __debug:
            print(
                f"DEBUG: PPpackage-utils: "
                f"resolver returned {json_dumps(resolution_graphs)}",
                file=stderr,
            )

        indent = 4 if __debug else None

        json_dump(resolution_graphs, stdout, indent=indent)

    @__app.command()
    async def fetch(cache_path: Path) -> None:
        input_json = json_load(stdin)

        input = FetchInput.model_validate(input_json)

        output = await fetch_callback(cache_path, input)

        indent = 4 if __debug else None

        json_dump(output.model_dump(), stdout, indent=indent)

    @__app.command()
    async def generate(cache_path: Path, generators_path: Path) -> None:
        input = json_load(stdin)

        input = parse_generate_input(__debug, input)

        product_ids = await generate_callback(
            cache_path,
            input.generators,
            generators_path,
            input.options,
            input.packages,
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

        products = products_parser(__debug, input)

        await install_callback(
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
