from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_epoch(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> str:
    return "0"
