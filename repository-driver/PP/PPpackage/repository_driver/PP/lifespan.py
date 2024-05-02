from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from .schemes import DriverParameters, RepositoryParameters
from .state import State


@asynccontextmanager
async def lifespan(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterator[State]:
    yield State()
