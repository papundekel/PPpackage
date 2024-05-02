from PPpackage.utils.rwlock import read as rwlock_read

from .epoch import get
from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_epoch(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> str:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        return get(repository_parameters.database_path / "epoch")
