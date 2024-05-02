from collections.abc import AsyncIterable

from aiosqlite import Connection

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, strip_version, transaction


async def query_provides(connection: Connection, name: str) -> AsyncIterable[str]:
    async with transaction(connection):
        async with connection.execute(
            "SELECT provide FROM provides WHERE name = ?", (name,)
        ) as cursor:
            async for row in cursor:
                yield row[0]


async def compute_product_info(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    return {
        f"pacman-{strip_version(provide)}": {"version": f"{version}"}
        async for provide in query_provides(state.connection, full_package_name)
    } | {
        f"pacman-{name}": {
            "version": f"{version}",
            "dependency-versions": {
                dependency[len("pacman-") :]: next(iter(product_infos.values()))[
                    "version"
                ]
                for dependency, product_infos in dependency_product_infos.items()
            },
        }
    }
