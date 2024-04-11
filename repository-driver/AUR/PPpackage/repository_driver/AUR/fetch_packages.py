from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> AsyncIterable[FetchPackageInfo]:
    yield FetchPackageInfo("pacman-conan-1.0.0", frozenset(["pacman-conan"]))
