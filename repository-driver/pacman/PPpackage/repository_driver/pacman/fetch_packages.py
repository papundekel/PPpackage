from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import Package, PackageVersion

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[PackageVersion]:
    yield PackageVersion("pacman", "x", "1.0.0", None)
