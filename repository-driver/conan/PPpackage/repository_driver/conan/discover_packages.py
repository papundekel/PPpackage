from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import DiscoveryPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def discover_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[DiscoveryPackageInfo]:
    yield DiscoveryPackageInfo("conan-openssl-3.1.0", frozenset(["conan-openssl"]))
    yield DiscoveryPackageInfo("conan-openssl-3.1.1", frozenset(["conan-openssl"]))
    yield DiscoveryPackageInfo("conan-nameof-0.10.1", frozenset(["conan-nameof"]))
