from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get
from .state import State


async def get_epoch(state: State) -> str:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        return get(state.database_path / "epoch")
