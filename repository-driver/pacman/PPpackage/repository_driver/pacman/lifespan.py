from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from sys import stderr

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .state import State


@asynccontextmanager
async def lifespan(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterator[State]:
    database_path = repository_parameters.database_path

    database_path.mkdir(parents=True, exist_ok=True)

    coroutine_lock = RWLock()
    file_lock = InterProcessReaderWriterLock(database_path / "lock")

    with (
        TemporaryDirectory() as root_directory_path,
        TemporaryDirectory() as cache_directory_path,
    ):
        handle = Handle(str(root_directory_path), str(database_path))

        handle.add_cachedir(str(cache_directory_path))

        yield State(coroutine_lock, file_lock, handle, cache_directory_path)
