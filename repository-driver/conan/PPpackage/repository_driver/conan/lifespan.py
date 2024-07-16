from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock

from PPpackage.utils.file import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import create_api_and_app


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

    homes_parent_path = database_path / "conan-homes"
    homes_parent_path.mkdir(exist_ok=True, parents=True)

    aux_homes = list[Path]()

    for _ in range(16):
        with TemporaryDirectory(homes_parent_path) as aux_home_path:
            with (aux_home_path / "global.conf").open("w") as file:
                file.write("tools.system.package_manager:mode = report\n")

            aux_homes.append(aux_home_path)

    main_home_path = homes_parent_path / "main"
    main_home_path.mkdir(exist_ok=True, parents=True)

    api, app = create_api_and_app(main_home_path)

    yield State(
        database_path,
        repository_parameters.url,
        repository_parameters.verify_ssl,
        coroutine_lock,
        file_lock,
        api,
        app,
        aux_homes,
    )
