from collections.abc import AsyncIterable, MutableSequence
from sys import stderr

from aiosqlite import Connection

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)
from PPpackage.utils.utils import Result

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


async def query_provides(connection: Connection) -> AsyncIterable[tuple[str, str, str]]:
    async with connection.execute(
        """
        SELECT packages.name, version, provide
        FROM packages JOIN provides
        ON packages.name = provides.name
        """
    ) as cursor:
        async for row in cursor:
            yield row[0], row[1], row[2]


def make_full_name(package_name: str, package_version: str) -> str:
    return f"pacman-real-{package_name}-{package_version}"


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    epoch_result: Result[str],
) -> AsyncIterable[Requirement]:
    provides = dict[str | tuple[str, str], MutableSequence[str]]()

    connection = state.connection

    async with transaction(connection):
        epoch_result.set(await get_epoch(connection))

        async for (
            package_name,
            package_version,
            dependency,
        ) in query_runtime_dependencies(connection):
            yield ImplicationRequirement(
                SimpleRequirement(
                    "noop", make_full_name(package_name, package_version)
                ),
                SimpleRequirement("pacman", dependency),
            )

        print("done with runtime dependencies", file=stderr)

        async for package_name, package_version, provide in query_provides(connection):
            provides.setdefault(provide, []).append(
                make_full_name(package_name, package_version)
            )

    print("done with provides db", file=stderr)

    for provide, packages in provides.items():
        variable_string = (
            provide if isinstance(provide, str) else f"{provide[0]}-{provide[1]}"
        )

        yield ImplicationRequirement(
            SimpleRequirement("noop", f"pacman-virtual-{variable_string}"),
            (
                XORRequirement(
                    [SimpleRequirement("noop", package) for package in packages]
                )
                if len(packages) > 1
                else SimpleRequirement("noop", packages[0])
            ),
        )

    print("done with provides dict", file=stderr)
