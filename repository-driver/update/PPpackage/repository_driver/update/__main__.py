from pathlib import Path
from typing import Annotated, Optional

from PPpackage.repository_driver.interface.interface import Interface
from typer import Option as TyperOption

from PPpackage.utils.cli import AsyncTyper, run
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_from_bytes

app = AsyncTyper()


def load_parameters(Parameters: type, path: Path | None):
    if path is None:
        return Parameters()

    with path.open("rb") as file:
        return load_from_bytes(Parameters, memoryview(file.read()))


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

    await interface.update(driver_parameters, repository_parameters)


run(app, "PPpackage update")
