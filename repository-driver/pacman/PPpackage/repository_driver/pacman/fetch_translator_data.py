from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.exceptions import EpochException
from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .get_epoch import get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .utils import package_provides


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
) -> AsyncIterable[TranslatorInfo]:
    if epoch != await get_epoch(driver_parameters, repository_parameters):
        raise EpochException

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)
        database.servers = repository_parameters.mirrorlist

        for package in database.pkgcache:
            yield TranslatorInfo(
                f"pacman-real-{package.name}",
                {"version": package.version},
            )

            for provide in package_provides(package.provides):
                match provide:
                    case library, version:
                        yield TranslatorInfo(
                            f"pacman-virtual-{library}", {"version": version}
                        )
                    case str():
                        yield TranslatorInfo(f"pacman-virtual-{provide}", {})
