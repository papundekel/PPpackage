from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import package_provides


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[TranslatorInfo]:
    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)
        database.servers = repository_parameters.mirrorlist

        for package in database.pkgcache:
            yield TranslatorInfo(
                f"pacman-{package.name}",
                package.version,
            )

            for provide in package_provides(package.provides):
                match provide:
                    case (library, version):
                        yield TranslatorInfo(f"pacman-{library}", version)
                    case str():
                        yield TranslatorInfo(f"pacman-{provide}", "")
