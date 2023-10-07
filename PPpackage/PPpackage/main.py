from pathlib import Path
from sys import stdin

from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.utils import json_load
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
    cache_path: Path,
    generators_path: Path,
    daemon_socket_path: Path,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    do_update_database: Annotated[bool, TyperOption("--update-database")] = False,
    debug: bool = False,
) -> None:
    requirements_generators_input = json_load(stdin)

    requirements, options, generators = parse_input(requirements_generators_input)

    if do_update_database:
        managers = requirements.keys()
        await update_database(debug, managers, cache_path)

    versions = await resolve(debug, cache_path, requirements, options)

    product_ids = await fetch(
        debug, cache_path, versions, options, generators, generators_path
    )

    await install(
        debug,
        cache_path,
        daemon_socket_path,
        daemon_workdir_path,
        destination_relative_path,
        versions,
        product_ids,
    )


def main():
    run(app, "PPpackage")
