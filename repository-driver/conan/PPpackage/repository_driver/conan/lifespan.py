from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import create_api_and_app

AUX_HOMES_COUNT = 16


def setup_home(home_path: Path):
    home_path.mkdir(parents=True, exist_ok=True)

    with (home_path / "global.conf").open("w") as file:
        file.write("tools.system.package_manager:mode = report\n")

    return home_path


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

    homes_path = database_path / "homes"
    homes_path.mkdir(parents=True, exist_ok=True)

    main_home_path = homes_path / "main"
    setup_home(main_home_path)

    api, app = create_api_and_app(main_home_path)

    aux_home_paths = [
        setup_home(homes_path / f"aux-{i}") for i in range(AUX_HOMES_COUNT)
    ]

    yield State(
        database_path,
        repository_parameters.url,
        repository_parameters.verify_ssl,
        coroutine_lock,
        file_lock,
        api,
        app,
        aux_home_paths,
    )
