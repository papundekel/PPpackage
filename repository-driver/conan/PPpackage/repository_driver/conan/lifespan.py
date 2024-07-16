from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiorwlock import RWLock
from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from fasteners import InterProcessReaderWriterLock

from PPpackage.utils.file import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import create_api_and_app


def setup_home(home_path: Path):
    with (home_path / "global.conf").open("w") as file:
        file.write("tools.system.package_manager:mode = report\n")


@asynccontextmanager
async def lifespan(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    data_path: Path,
) -> AsyncIterator[State]:
    database_path = (
        repository_parameters.database_path
        if repository_parameters.database_path is not None
        else data_path
    )

    coroutine_lock = RWLock()
    file_lock = InterProcessReaderWriterLock(database_path / "lock")

    home_path = database_path / "conan-home"
    home_path.mkdir(exist_ok=True, parents=True)

    setup_home(home_path)

    api, app = create_api_and_app(home_path)

    yield State(
        database_path,
        repository_parameters.url,
        repository_parameters.verify_ssl,
        coroutine_lock,
        file_lock,
        api,
        app,
    )
