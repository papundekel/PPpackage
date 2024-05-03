from collections.abc import AsyncIterable

from aiosqlite import Connection
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    BuildContextDetail,
    MetaBuildContextDetail,
    ProductInfos,
    SimpleRequirement,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, transaction


async def query_build_dependencies(
    connection: Connection, name: str
) -> AsyncIterable[str]:
    async with connection.execute(
        "SELECT dependency FROM build_dependencies WHERE name = ?", (name,)
    ) as cursor:
        async for row in cursor:
            yield row[0]


async def get_build_context(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    connection = state.connection

    async with transaction(connection):
        return MetaBuildContextDetail(
            ANDRequirement(
                [
                    SimpleRequirement("pacman", dependency)
                    async for dependency in query_build_dependencies(connection, name)
                ]
            ),
            options=None,
            on_top=True,
        )
