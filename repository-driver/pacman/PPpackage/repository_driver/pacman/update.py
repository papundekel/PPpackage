from shutil import move

from PPpackage.utils.lock.rw import write as rwlock_write

from .epoch import update as update_epoch
from .state import State


async def update(state: State) -> None:
    async with rwlock_write(state.coroutine_lock, state.file_lock):
        state.database.update(True)

        sync_database_path = state.database_path / "sync"

        move(
            sync_database_path / f"{state.repository}.db",
            sync_database_path / "database.db",
        )

        update_epoch(state.database_path / "epoch")
