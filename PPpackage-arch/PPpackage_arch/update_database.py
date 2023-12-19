from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from pathlib import Path

from PPpackage_utils.utils import (
    SubmanagerCommandFailure,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
)

from .utils import get_cache_paths


async def update_database(debug: bool, data: None, cache_path: Path):
    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    async with fakeroot(debug) as environment:
        process = await create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--sync",
            "--refresh",
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=DEVNULL,
            env=environment,
        )

        await asubprocess_wait(process, SubmanagerCommandFailure())
