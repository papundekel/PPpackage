from pathlib import Path

from PPpackage_utils.submanager import AsyncTyper, run
from typer import Option as TyperOption
from typing_extensions import Annotated

from .main import main

app = AsyncTyper()


@app.command()
async def main_command(
    runner_path: Path,
    runner_workdirs_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
    resolve_iteration_limit: int = 10,
) -> None:
    await main(
        debug,
        do_update_database,
        runner_path,
        runner_workdirs_path,
        cache_path,
        generators_path,
        destination_path,
        resolve_iteration_limit,
    )


run(app, "PPpackage")
