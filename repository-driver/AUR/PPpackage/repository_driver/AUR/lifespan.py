from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiosqlite import connect as sqlite_connect

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
        else data_path / "database"
    )

    database_path.mkdir(parents=True, exist_ok=True)

    async with sqlite_connect(
        database_path / "database.sqlite", autocommit=False
    ) as connection:
        yield State(database_path, connection)
