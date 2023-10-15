from pathlib import Path
from sys import stderr, stdin

from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.utils import json_dumps, json_load
from typer import Option as TyperOption
from typing_extensions import Annotated

from .fetch import fetch
from .install import install
from .parse import parse_input
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
    requirements_generators_input = json_load(stdin)

    requirements, options, generators = parse_input(
        debug, requirements_generators_input
    )

    if debug:
        print(
            f"DEBUG PPpackage: after parse, requirements: {json_dumps(requirements)}",
            file=stderr,
        )

    if do_update_database:
        managers = requirements.keys()
        await update_database(debug, managers, cache_path)

    versions = await resolve(
        debug, resolve_iteration_limit, cache_path, requirements, options
    )

    if debug:
        print(
            f"DEBUG PPpackage: after resolve, versions: {json_dumps(versions)}",
            file=stderr,
        )

    product_ids = await fetch(
        debug,
        runner_path,
        runner_workdir_path,
        cache_path,
        versions,
        options,
        generators,
        generators_path,
    )

    if debug:
        print("DEBUG PPpackage: after fetch", file=stderr)

    await install(
        debug,
        cache_path,
        runner_path,
        runner_workdir_path,
        destination_path,
        versions,
        product_ids,
    )

    if debug:
        print("DEBUG PPpackage: after install", file=stderr)


def main():
    run(app, "PPpackage")
