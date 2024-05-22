from typing import Any

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .state import State


async def translate_options(state: State, options: Any) -> tuple[str, None]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch = get_epoch(state.database_path / "epoch")

    return epoch, None
