from typing import Any

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> ConanOptions:
    return {}
