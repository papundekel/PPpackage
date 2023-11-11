from asyncio import run as asyncio_run
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from functools import partial, wraps
from inspect import iscoroutinefunction
from pathlib import Path
from sys import exit, stderr, stdin, stdout
from typing import Any, TypeVar

from PPpackage_utils.parse import (
    FetchInput,
    FetchOutput,
    GenerateInput,
    GenerateInputPackagesValue,
    ResolveInput,
    model_dump,
    model_validate,
)
from typer import Typer

from .utils import (
    MyException,
    Product,
    ResolutionGraph,
    ensure_dir_exists,
    json_dump,
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


T = TypeVar("T")


def init(
    update_database_callback: Callable[[Path], Awaitable[None]],
    resolve_callback: Callable[
        [Path, ResolveInput[T]], Awaitable[Set[ResolutionGraph]]
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
    RequirementType: type[T],
    products_parser: Callable[[bool, Any], Set[Product]],
) -> Typer:
    @__app.command("update-database")
    async def update_database(cache_path: Path) -> None:
        await update_database_callback(cache_path)

    @__app.command()
    async def resolve(cache_path: Path) -> None:
        input_json_bytes = stdin.buffer.read()

        input = model_validate(ResolveInput[RequirementType], input_json_bytes)

        resolution_graphs = await resolve_callback(cache_path, input)

        json_dump(resolution_graphs, stdout, indent=4 if __debug else None)

    @__app.command()
    async def fetch(cache_path: Path) -> None:
        input_json_bytes = stdin.buffer.read()

        input = model_validate(FetchInput, input_json_bytes)

        output = await fetch_callback(cache_path, input)

        output_json_bytes = model_dump(__debug, output)

        stdout.buffer.write(output_json_bytes)

    @__app.command()
    async def generate(cache_path: Path, generators_path: Path) -> None:
        input_json_bytes = stdin.buffer.read()

        input = model_validate(GenerateInput, input_json_bytes)

        await generate_callback(
            cache_path,
            input.generators,
            generators_path,
            input.options,
            input.packages,
        )

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
