from collections.abc import AsyncIterable

from aiosqlite import Connection
from PPpackage.repository_driver.interface.schemes import Requirement
from PPpackage.utils.async_ import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import transaction


async def query_runtime_dependencies(
    connection: Connection,
) -> AsyncIterable[tuple[str, str, str]]:
    async with connection.execute(
        """
        SELECT packages.name, version, dependency
        FROM packages JOIN runtime_dependencies
        ON packages.name = runtime_dependencies.name
        """
    ) as cursor:
        async for row in cursor:
            yield row[0], row[1], row[2]


async def query_conflicts(
    connection: Connection,
) -> AsyncIterable[tuple[str, str, str]]:
    async with connection.execute(
        """
        SELECT packages.name, version, conflict
        FROM packages JOIN conflicts
        ON packages.name = conflicts.name
        """
    ) as cursor:
        async for row in cursor:
            yield row[0], row[1], row[2]


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    epoch_result: Result[str],
) -> AsyncIterable[list[Requirement]]:
    connection = state.connection

    async with transaction(connection):
        epoch_result.set(await get_epoch(connection))

        async for name, version, dependency in query_runtime_dependencies(connection):
            yield [
                Requirement("noop", f"pacman-{name}-{version}", False),
                Requirement("pacman", dependency),
            ]

        async for name, version, conflict in query_conflicts(connection):
            yield [
                Requirement("noop", f"pacman-{name}-{version}", False),
                Requirement(
                    "pacman",
                    {"package": conflict, "exclude": f"{name}-{version}"},
                    False,
                ),
            ]
