from pathlib import Path
from typing import Optional

from PPpackage_utils.submanager import AsyncTyper, run
from PPpackage_utils.validation import load_from_bytes
from typer import Option as TyperOption
from typing_extensions import Annotated

from .main import main
from .parse import Config

app = AsyncTyper()


@app.command()
async def main_command(
    config_path: Path,
    destination_path: Path,
    generators_path: Annotated[Optional[Path], TyperOption("--generators")] = None,
    graph_path: Annotated[Optional[Path], TyperOption("--graph")] = None,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
    resolve_iteration_limit: int = 10,
) -> None:
    with config_path.open("rb") as config_file:
        config_bytes = config_file.read()

        config = load_from_bytes(debug, Config, config_bytes)

        await main(
            debug,
            do_update_database,
            config.submanager_socket_paths,
            destination_path,
            generators_path,
            graph_path,
            resolve_iteration_limit,
        )


run(app, "PPpackage")
