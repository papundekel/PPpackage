from collections.abc import AsyncIterable

from aiosqlite import Connection
from PPpackage.repository_driver.interface.schemes import (
    BuildContextInfo,
    ProductInfo,
    ProductInfos,
)

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
    translated_options: None,
    full_package_name: str,
    build_context_info: BuildContextInfo,
    runtime_product_infos: ProductInfos,
) -> ProductInfo:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    connection = state.connection

    return {
        f"pacman-{strip_version(provide)}": {"version": f"{version}"}
        async for provide in query_provides(connection, full_package_name)
    } | {
        f"pacman-{name}": {
            "version": f"{version}",
            "dependency-versions": {
                dependency[len("pacman-") :]: next(iter(product_infos.values()))[
                    "version"
                ]
                for dependency, product_infos in runtime_product_infos.items()
            },
        }
    }
