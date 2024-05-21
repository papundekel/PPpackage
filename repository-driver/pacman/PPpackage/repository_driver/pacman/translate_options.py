from typing import Any

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def translate_options(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> tuple[str, None]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch = get_epoch(repository_parameters.database_path / "epoch")

    return epoch, None
