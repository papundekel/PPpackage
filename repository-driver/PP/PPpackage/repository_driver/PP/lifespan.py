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
    yield State()
