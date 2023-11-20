from collections.abc import MutableMapping, MutableSequence
from pathlib import Path
from sys import stderr, stdin

from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.parse import Product, ProductBase, load_bytes
from typer import Option as TyperOption
from typing_extensions import Annotated

from .fetch import fetch
from .generate import generate
from .install import install
from .parse import Input
from .resolve import resolve
from .update_database import update_database

app = AsyncTyper()


@app.command()
async def main_command(
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
    resolve_iteration_limit: int = 10,
) -> None:
    input_json_bytes = stdin.buffer.read()

    input = load_bytes(debug, Input, input_json_bytes)

    if do_update_database:
        managers = input.requirements.keys()
        await update_database(debug, managers, cache_path)

    graph = await resolve(
        debug, resolve_iteration_limit, cache_path, input.requirements, input.options
    )

    await fetch(
        debug,
        runner_path,
        runner_workdir_path,
        cache_path,
        input.options,
        graph,
    )

    meta_products: MutableMapping[str, MutableSequence[Product]] = {}

    for (manager, name), data in graph.nodes(data=True):
        meta_products.setdefault(manager, []).append(
            Product(
                name=name,
                version=data["version"],
                product_id=data["product_id"],
            )
        )

    await generate(
        debug,
        cache_path,
        generators_path,
        input.generators,
        meta_products,
        input.options,
    )

    await install(
        debug,
        cache_path,
        runner_path,
        runner_workdir_path,
        destination_path,
        meta_products,
    )

    if debug:
        print("DEBUG PPpackage: after install", file=stderr)


def main():
    run(app, "PPpackage")
