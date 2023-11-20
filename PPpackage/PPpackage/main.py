from collections.abc import MutableMapping, MutableSet
from pathlib import Path
from sys import stderr, stdin

from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.parse import GenerateInputPackagesValue, Product, model_validate
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

    input = model_validate(debug, Input, input_json_bytes)

    if do_update_database:
        managers = input.requirements.keys()
        await update_database(debug, managers, cache_path)

    graph = await resolve(
        debug, resolve_iteration_limit, cache_path, input.requirements, input.options
    )

    fetch_outputs = await fetch(
        debug,
        runner_path,
        runner_workdir_path,
        cache_path,
        graph,
        input.options,
    )

    meta_versions = {}

    for (manager, package), data in graph.nodes(data=True):
        meta_versions.setdefault(manager, {})[package] = data["version"]

    meta_product_ids = {
        manager: {package: value.product_id for package, value in values.items()}
        for manager, values in fetch_outputs.items()
    }

    meta_products: MutableMapping[str, MutableSet[Product]] = {}

    for manager, versions in meta_versions.items():
        for package, version in versions.items():
            meta_products.setdefault(manager, set()).add(
                Product(
                    package=package,
                    version=version,
                    product_id=meta_product_ids[manager][package],
                )
            )

    meta_packages = {
        manager: {
            product.package: GenerateInputPackagesValue(
                version=product.version, product_id=product.product_id
            )
            for product in products
        }
        for manager, products in meta_products.items()
    }

    await generate(
        debug,
        cache_path,
        generators_path,
        input.generators,
        meta_packages,
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
