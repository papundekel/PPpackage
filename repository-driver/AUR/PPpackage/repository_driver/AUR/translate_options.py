from typing import Any

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import transaction


async def translate_options(state: State, options: Any) -> tuple[str, None]:
    connection = state.connection

    async with transaction(connection):
        epoch = await get_epoch(connection)

    return epoch, None
