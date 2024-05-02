from .epoch import get
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import transaction


async def get_epoch(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> str:
    connection = state.connection

    async with transaction(connection):
        return await get(connection)
