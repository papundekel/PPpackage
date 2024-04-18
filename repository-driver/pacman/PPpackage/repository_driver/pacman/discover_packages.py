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
            full_name: str = package.name
            package_name = full_name.rsplit("-1", 3)[0]

            yield DiscoveryPackageInfo(
                f"pacman-{full_name}",
                frozenset([f"pacman-{package_name}"]),
            )
