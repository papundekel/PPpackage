from typing import Any

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def translate_options(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> tuple[str, None]:
    return "0", None
