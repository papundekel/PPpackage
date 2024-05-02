from collections.abc import AsyncIterable

from aiosqlite import Connection
from asyncstdlib import chain as async_chain
from asyncstdlib import list as async_list

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    MetaOnTopProductDetail,
    PackageDetail,
    SimpleRequirement,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, strip_version, transaction


async def query_version(connection: Connection, name: str) -> str:
    async with connection.execute(
        "SELECT version FROM packages WHERE name = ?", (name,)
    ) as cursor:
        row = await cursor.fetchone()

        if row is None:
            raise Exception(f"Package not found: {name}")

        return row[0]


async def query_provides(connection: Connection, name: str) -> AsyncIterable[str]:
    async with connection.execute(
        "SELECT provide FROM provides WHERE name = ?", (name,)
    ) as cursor:
        async for row in cursor:
            yield row[0]


async def query_runtime_dependencies(
    connection: Connection, name: str
) -> AsyncIterable[str]:
    async with connection.execute(
        "SELECT dependency FROM runtime_dependencies WHERE name = ?", (name,)
    ) as cursor:
        async for row in cursor:
            yield row[0]


async def query_build_dependencies(
    connection: Connection, name: str
) -> AsyncIterable[str]:
    async with connection.execute(
        "SELECT dependency FROM build_dependencies WHERE name = ?", (name,)
    ) as cursor:
        async for row in cursor:
            yield row[0]


async def get_package_detail(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    name, version = parse_package_name(full_package_name)

    connection = state.connection

    async with transaction(connection):
        package_version = await query_version(connection, name)

        if package_version != version:
            return None

        return PackageDetail(
            frozenset(
                await async_list(
                    async_chain(
                        [f"pacman-{name}"],
                        (
                            f"pacman-{strip_version(provide)}"
                            async for provide in query_provides(connection, name)
                        ),
                    )
                )
            ),
            frozenset(
                [
                    f"pacman-{strip_version(dependency)}"
                    async for dependency in query_runtime_dependencies(connection, name)
                ]
            ),
            MetaOnTopProductDetail(
                ANDRequirement(
                    [
                        SimpleRequirement("pacman", dependency)
                        async for dependency in query_build_dependencies(
                            connection, name
                        )
                    ]
                )
            ),
        )
