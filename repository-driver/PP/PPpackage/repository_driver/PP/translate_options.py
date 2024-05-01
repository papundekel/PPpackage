from typing import Any

from .schemes import DriverParameters, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
    options: Any,
):
    return None
