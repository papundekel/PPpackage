from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import PackageVersion

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[PackageVersion]:
    yield PackageVersion("PP", "x", "1.0.0", None)
