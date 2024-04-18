from collections.abc import AsyncIterable
from sys import stderr

from PPpackage.repository_driver.interface.schemes import DiscoveryPackageInfo
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters


async def discover_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[DiscoveryPackageInfo]:
    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)
        database.servers = repository_parameters.mirrorlist

        for package in database.pkgcache:
            yield DiscoveryPackageInfo(
                f"pacman-{package.name}-{package.version}-{package.arch}",
                frozenset([f"pacman-{package.name}"]),
            )
