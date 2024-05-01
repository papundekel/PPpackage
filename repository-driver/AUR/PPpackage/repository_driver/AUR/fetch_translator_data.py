from collections.abc import AsyncIterable, Iterable
from typing import cast as type_cast

from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from sqlitedict import SqliteDict

from .schemes import AURPackage, DriverParameters, RepositoryParameters
from .utils import package_provides


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
) -> AsyncIterable[TranslatorInfo]:
    with SqliteDict(
        repository_parameters.database_path / "database.sqlite",
        tablename="packages",
    ) as database:
        for package in type_cast(Iterable[AURPackage], database.values()):
            yield TranslatorInfo(
                f"pacman-real-{package.Name}",
                {"version": package.Version},
            )

            for provide in package_provides(package.Provides):
                match provide:
                    case library, version:
                        yield TranslatorInfo(
                            f"pacman-virtual-{library}", {"version": version}
                        )
                    case str():
                        yield TranslatorInfo(f"pacman-virtual-{provide}", {})
