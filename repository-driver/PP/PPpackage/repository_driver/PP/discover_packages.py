from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import DiscoveryPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def discover_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[DiscoveryPackageInfo]:
    yield DiscoveryPackageInfo("PP-p1-1.0.0", frozenset(["PP-p1"]))
    yield DiscoveryPackageInfo("PP-p2-1.0.0", frozenset(["PP-p2"]))
    yield DiscoveryPackageInfo("PP-p3-1.0.0", frozenset(["PP-p3"]))
