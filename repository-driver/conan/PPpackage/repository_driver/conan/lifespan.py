from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiorwlock import RWLock
from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from fasteners import InterProcessReaderWriterLock

from .schemes import DriverParameters, RepositoryParameters
from .state import State


@asynccontextmanager
async def lifespan(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterator[State]:
    database_path = repository_parameters.database_path

    coroutine_lock = RWLock()
    file_lock = InterProcessReaderWriterLock(database_path / "lock")
    api = ConanAPI(str(database_path.absolute() / "cache"))
    app = ConanApp(api)

    yield State(coroutine_lock, file_lock, api, app)
