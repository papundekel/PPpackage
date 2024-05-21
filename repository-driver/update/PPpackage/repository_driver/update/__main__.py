from pathlib import Path
from typing import Annotated, Optional

from PPpackage.repository_driver.interface.interface import Interface
from typer import Option as TyperOption

from PPpackage.utils.cli import AsyncTyper
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import validate_json_io_path

app = AsyncTyper()


def load_parameters(Parameters: type, path: Path | None):
    if path is None:
        return Parameters()

    return validate_json_io_path(Parameters, path)


@app.command()
async def main(
    package: str,
    driver_parameters_path: Annotated[Optional[Path], TyperOption("--driver")] = None,
    repository_parameters_path: Annotated[
        Optional[Path], TyperOption("--repository")
    ] = None,
):
    interface = load_interface_module(Interface, package)

    driver_parameters = load_parameters(
        interface.DriverParameters, driver_parameters_path
    )

    repository_parameters = load_parameters(
        interface.RepositoryParameters, repository_parameters_path
    )

    async with interface.lifespan(driver_parameters, repository_parameters) as state:
        await interface.update(state, driver_parameters, repository_parameters)


app()
