from collections.abc import AsyncIterable, Mapping
from typing import Any

from PPpackage.repository_driver.interface.schemes import PackageVersion

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Mapping[str, Any],
) -> AsyncIterable[PackageVersion]:
    yield PackageVersion("conan", "x", "1.0.0", None)
