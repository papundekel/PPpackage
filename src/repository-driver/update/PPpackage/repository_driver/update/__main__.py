from pathlib import Path
from typing import Annotated, Optional

from PPpackage.repository_driver.interface.interface import Interface
from typer import Option as TyperOption

from PPpackage.utils.cli import App
from PPpackage.utils.json.validate import validate_json_io_path
from PPpackage.utils.python import load_interface_module

app = App()


def load_parameters(Parameters: type, path: Path | None):
    if path is None:
        return Parameters()

    return validate_json_io_path(Parameters, path)


@app.command()
async def main(
    package: str,
    name: str,
    data_path: Optional[Path] = None,
    driver_config_path: Annotated[
        Optional[Path], TyperOption("--driver-config")
    ] = None,
    repository_config_path: Annotated[
        Optional[Path], TyperOption("--repository-config")
    ] = None,
):
    if data_path is None:
        data_path = Path.home() / ".PPpackage" / "repository" / str(name)

    interface = load_interface_module(Interface, package)

    driver_parameters = load_parameters(interface.DriverParameters, driver_config_path)

    repository_parameters = load_parameters(
        interface.RepositoryParameters, repository_config_path
    )

    async with interface.lifespan(
        driver_parameters, repository_parameters, data_path
    ) as state:
        await interface.update(state)


app()
