from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def update(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    pass
