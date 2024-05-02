from collections.abc import AsyncIterable

from aiosqlite import Connection

from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from PPpackage.utils.utils import Result

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import parse_provide, transaction


async def query_packages(connection: Connection) -> AsyncIterable[tuple[str, str]]:
    async with connection.execute("SELECT * FROM packages") as cursor:
        async for row in cursor:
            yield row[0], row[1]


async def query_provides(connection: Connection) -> AsyncIterable[str]:
    async with connection.execute("SELECT provide FROM provides") as cursor:
        async for row in cursor:
            yield row[0]


async def fetch_translator_data(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch_result: Result[str],
) -> AsyncIterable[TranslatorInfo]:
    connection = state.connection

    async with transaction(connection):
        async for package_name, package_version in query_packages(connection):
            yield TranslatorInfo(
                f"pacman-real-{package_name}",
                {"version": package_version},
            )

        async for provide in query_provides(connection):
            match parse_provide(provide):
                case library, version:
                    yield TranslatorInfo(
                        f"pacman-virtual-{library}", {"version": version}
                    )
                case str():
                    yield TranslatorInfo(f"pacman-virtual-{provide}", {})
