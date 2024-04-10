from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[FetchPackageInfo]:
    yield FetchPackageInfo("conan-x-1.0.0", frozenset(["conan-x"]))
    yield FetchPackageInfo("conan-x-1.0.1", frozenset(["conan-x"]))
    yield FetchPackageInfo("conan-y-1.0.0", frozenset(["conan-y"]))
