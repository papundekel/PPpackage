from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiosqlite import connect as sqlite_connect

from .schemes import DriverParameters, RepositoryParameters
from .state import State


@asynccontextmanager
async def lifespan(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterator[State]:
    database_path = repository_parameters.database_path

    async with sqlite_connect(
        database_path / "database.sqlite", autocommit=False
    ) as connection:
        yield State(connection)
