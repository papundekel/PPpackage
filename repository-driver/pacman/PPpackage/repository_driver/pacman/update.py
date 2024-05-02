from shutil import move

from PPpackage.utils.rwlock import write as rwlock_write

from .epoch import update as update_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def update(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    async with rwlock_write(state.coroutine_lock, state.file_lock):
        state.database.update(True)

        sync_database_path = repository_parameters.database_path / "sync"

        move(
            sync_database_path / f"{repository_parameters.repository}.db",
            sync_database_path / "database.db",
        )

        update_epoch(repository_parameters.database_path / "epoch")
