from collections.abc import MutableMapping, MutableSet
from pathlib import Path
from sys import stderr, stdin

from networkx.drawing.nx_pydot import to_pydot
from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.parse import Product, model_validate
from PPpackage_utils.utils import json_dumps
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
    do_update_database: Annotated[bool, TyperOption("--update-database")] = False,
    debug: bool = False,
    resolve_iteration_limit: int = 10,
) -> None:
    input_json_bytes = stdin.buffer.read()

    input = model_validate(debug, Input, input_json_bytes)

    if debug:
        print(
            f"DEBUG PPpackage: after parse, "
            f"requirements: {json_dumps(input.requirements)}",
            file=stderr,
        )

    if do_update_database:
        managers = input.requirements.keys()
        await update_database(debug, managers, cache_path)

    graph = await resolve(
        debug, resolve_iteration_limit, cache_path, input.requirements, input.options
    )

    if debug:
        print(
            f"DEBUG PPpackage: after resolve, graph:\n {to_pydot(graph).to_string()}",
            file=stderr,
        )

    fetch_outputs = await fetch(
        debug,
        runner_path,
        runner_workdir_path,
        cache_path,
        graph,
        input.options,
    )

    if debug:
        print("DEBUG PPpackage: after fetch", file=stderr)

    meta_versions = {}

    for (manager, package), data in graph.nodes(data=True):
        meta_versions.setdefault(manager, {})[package] = data["version"]

    product_ids = {
        manager: {package: value.product_id for package, value in values.items()}
        for manager, values in fetch_outputs.items()
    }

    await generate(
        debug,
        cache_path,
        input.generators,
        generators_path,
        input.options,
        meta_versions,
        product_ids,
    )

    meta_products: MutableMapping[str, MutableSet[Product]] = {}

    for manager, versions in meta_versions.items():
        for package, version in versions.items():
            meta_products.setdefault(manager, set()).add(
                Product(
                    package=package,
                    version=version,
                    product_id=product_ids[manager][package],
                )
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
