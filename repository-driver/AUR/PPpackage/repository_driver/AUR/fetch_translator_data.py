from collections.abc import AsyncIterable

from aiosqlite import Connection
from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from PPpackage.utils.utils import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import parse_provide, transaction


async def query_packages(connection: Connection) -> AsyncIterable[tuple[str, str]]:
    async with connection.execute("SELECT * FROM packages") as cursor:
        async for row in cursor:
            yield row[0], row[1]


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


async def fetch_translator_data(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch_result: Result[str],
) -> AsyncIterable[TranslatorInfo]:
    connection = state.connection

    async with transaction(connection):
        epoch_result.set(await get_epoch(connection))

        async for name, version in query_packages(connection):
            yield TranslatorInfo(f"pacman-{name}", {"version": version, "AUR": ""})

        async for name, version, provide in query_provides(connection):
            provider = f"{name}-{version}"

            match parse_provide(provide):
                case provide_name, provide_version:
                    yield TranslatorInfo(
                        f"pacman-{provide_name}",
                        {"provider": provider, "version": provide_version, "AUR": ""},
                    )
                case provide_name:
                    yield TranslatorInfo(
                        f"pacman-{provide_name}", {"provider": provider, "AUR": ""}
                    )
