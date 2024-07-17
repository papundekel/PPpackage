from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock
from httpx import Client as HTTPClient
from pyalpm import Handle

from PPpackage.utils.file import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .state import State


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

    database_path.mkdir(parents=True, exist_ok=True)

    coroutine_lock = RWLock()
    file_lock = InterProcessReaderWriterLock(database_path / "lock")

    with (
        HTTPClient() as http_client,
        TemporaryDirectory() as root_directory_path,
        TemporaryDirectory() as cache_directory_path,
    ):
        handle = Handle(str(root_directory_path), str(database_path))

        handle.add_cachedir(str(cache_directory_path))

        repository = (
            repository_parameters.repository
            if repository_parameters.repository is not None
            else "database"
        )

        database = handle.register_syncdb(repository, 0)
        database.servers = repository_parameters.mirrorlist

        yield State(
            database_path,
            repository,
            coroutine_lock,
            file_lock,
            handle,
            cache_directory_path,
            database,
            http_client,
        )
