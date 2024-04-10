from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[FetchPackageInfo]:
    yield FetchPackageInfo("PP-p1-1.0.0", frozenset(["PP-p1"]))
    yield FetchPackageInfo("PP-p2-1.0.0", frozenset(["PP-p2"]))
