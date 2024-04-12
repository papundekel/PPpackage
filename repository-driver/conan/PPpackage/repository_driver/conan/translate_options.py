from collections.abc import Mapping
from typing import Any

from .schemes import DriverParameters, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> Mapping[str, Any]:
    return {}