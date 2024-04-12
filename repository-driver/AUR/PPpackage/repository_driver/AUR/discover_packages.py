from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import DiscoveryPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def discover_packages(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterable[DiscoveryPackageInfo]:
    yield DiscoveryPackageInfo("pacman-conan-1.0.0", frozenset(["pacman-conan"]))
