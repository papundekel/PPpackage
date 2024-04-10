from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[FetchPackageInfo]:
    yield FetchPackageInfo("PP-x-1.0.0", frozenset(["PP-x"]))
    yield FetchPackageInfo("PP-x-1.0.1", frozenset(["PP-x"]))
    yield FetchPackageInfo("PP-y-1.0.0", frozenset(["PP-y"]))
